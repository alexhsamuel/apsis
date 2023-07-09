import asyncio
import functools
import logging
import ora
import procstar
from   procstar.spec import Proc
import socket
import traceback

from   .base import (
    Program, ProgramRunning, ProgramSuccess, ProgramFailure, ProgramError,
    program_outputs, Timeout,
)
from   apsis.host_group import expand_host
from   apsis.lib.cmpr import compress_async
from   apsis.lib.json import check_schema
from   apsis.lib.net import NetAddress
from   apsis.lib.py import or_none
from   apsis.lib.sys import get_username
from   apsis.runs import template_expand, join_args

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.
nto_jso = lambda obj: None if obj is None else obj.to_jso()
nfrom_jso = lambda cls: or_none(cls.from_jso)


def _bind_addr(addr, args):
    host, port = addr
    host = template_expand(host, args)
    port = int(template_expand(port, args))
    return NetAddress(host, port)


class ExecProgram(Program):

    def __init__(self, addr, argv, *, timeout=None):
        super().__init__()
        self.__addr     = NetAddress.split(addr)
        self.__argv     = tuple( str(a) for a in argv )
        self.__timeout  = timeout


    def __str__(self):
        return join_args(self.__addr, self.__argv, timeout=self.__timeout)


    def to_jso(self):
        return {
            **super().to_jso(),
            "addr"      : self.__addr,
            "argv"      : self.__argv,
            "timeout"   : nto_jso(self.__timeout),
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            addr    = pop("addr")
            argv    = pop("argv", tuple)
            timeout = pop("timeout", nfrom_jso(Timeout), None)
        return cls(addr, argv, timeout=timeout)


    def bind(self, args):
        addr    = _bind_addr(self.__addr, args)
        argv    = tuple( template_expand(a, args) for a in self.__argv )
        timeout = None if self.__timeout is None else self.__timeout.bind(args)
        return BoundProgram(addr, argv, timeout=timeout)



class CommandProgram(Program):

    def __init__(self, addr, command, *, timeout=None):
        super().__init__()
        self.__addr = addr
        self.__command = str(command)
        self.__timeout = timeout


    def __str__(self):
        return join_args(self.__addr, self.__command, timeout=self.__timeout)


    def to_jso(self):
        return {
            **super().to_jso(),
            "addr"      : self.__addr,
            "command"   : self.__command,
            "timeout"   : nto_jso(self.__timeout),
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            addr    = pop("addr")
            command = pop("command", str)
            timeout = pop("timeout", nfrom_jso(Timeout), None)
        return cls(addr, command, timeout=timeout)


    def bind(self, args):
        addr    = _bind_addr(self.__addr, args)
        command = template_expand(self.__command, args)
        argv    = ["/bin/bash", "-c", command]
        timeout = None if self.__timeout is None else self.__timeout.bind(args)
        return BoundProgram(addr, argv, timeout=timeout)



#-------------------------------------------------------------------------------

class BoundProgram(Program):

    def __init__(self, addr, argv, *, timeout=None):
        self.__addr = NetAddress.convert(addr)
        self.__argv = [ str(a) for a in argv ]
        self.__timeout = timeout


    def to_jso(self):
        return {
            "addr"      : self.__addr.to_jso(),
            "argv"      : self.__argv,
            "timeout"   : nto_jso(self.__timeout),
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            addr = pop("addr", NetAddress.from_jso)
            argv = pop("argv", list)
            timeout = pop("timeout", nfrom_jso(Timeout), None)
        return cls(addr, argv, timeout=timeout)


    @functools.cached_property
    def __client(self):
        return procstar.client.AsyncClient(
            self.__addr.host, self.__addr.port, get_http_client())


    async def start(self, run_id, cfg):
        # FIXME: expand_host() should probably act on addres, not hosts.
        addr = NetAddress(expand_host(self.__addr.host, cfg), self.__addr.port)
        argv = self.__argv

        log.debug(f"starting program at {addr}: {join_args(argv)}")

        env = {
            "APSIS_RUN_ID": run_id,
            # FIXME: Other things?
        }
        spec = Proc(
            argv,
            env=Proc.Env(inherit=True, vars=env),
            fds={
                "stdin" : Proc.Fd.Null(),
                "stdout": Proc.Fd.Capture("memory"),
                "stderr": Proc.Fd.Dup("stdout"),
            },
        )

        meta = {
            "apsis_hostname"  : socket.gethostname(),
            "apsis_username"  : get_username(),
        }

        try:
            proc_id = self.__client.post_proc(spec)
        except Exception as exc:
            log.error("failed to start program", exc_info=True)
            output = traceback.format_exc().encoded()
            # FIXME: Use a different "traceback" output, once the UI can
            # understand it.
            raise ProgramError(
                message=str(exc), outputs=program_outputs(output))
            log.info(f"started proc: {proc_id}")

        # FIXME: Make sure we distinguish an err where the proc isn't created,
        # from an err where the proc is created (but e.g. fails to start).

        run_state = {
            "addr": addr.to_jso(),
            "proc_id": proc_id,
            # FIXME: pid,
        }
        meta.update(run_state)
        # FIXME: Propagate times from agent.
        # FIXME: Do this asynchronously from the agent instead.
        done = self.wait(run_id, run_state)
        run_state["start"] = str(ora.now())
        return ProgramRunning(run_state, meta=meta), done


    async def wait(self, run_id, run_state):
        addr = NetAddress.from_jso(run_state["addr"])
        proc_id = run_state["proc_id"]

        if self.__timeout is not None:
            start = ora.Time(run_state["start"])

        explanation = ""

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1
        while True:
            if self.__timeout is not None:
                elapsed = ora.now() - start
                if self.__timeout.duration < elapsed:
                    msg = f"timeout after {elapsed:.0f} s"
                    log.info(f"{run_id}: {msg}")
                    explanation = f" ({msg})"
                    # FIXME: Note timeout in run log.
                    await self.signal(run_id, run_state, self.__timeout.signal)
                    await asyncio.sleep(POLL_INTERVAL)

            log.debug(f"polling proc: {run_id}: {proc_id} @ {addr}")
            proc = await self.__client.get_proc(proc_id)
            # except NoSuchProcessError:
            #     # Agent doesn't know about this process anymore.
            #     raise ProgramError(f"program lost: {run_id}")
            if proc["status"] is None:
                await asyncio.sleep(POLL_INTERVAL)
            else:
                break

        status = proc["status"]

        # FIXME: Get output separately.
        output = proc["fds"]["stdout"]["text"]
        length = len(output)
        # FIXME: Handle compression in procstar.
        compression = None

        if compression is None and len(output) > 16384:
            # Compress the output.
            try:
                output, compression = await compress_async(output, "br"), "br"
            except RuntimeError as exc:
                log.error(f"{exc}; not compressing")

        outputs = program_outputs(
            output, length=length, compression=compression)
        log.debug(f"got output: {length} bytes, {compression or 'uncompressed'}")

        try:
            if status["status"] == 0:
                return ProgramSuccess(meta=proc, outputs=outputs)

            else:
                # FIXME: We have more details now.
                message = f"program failed: status {status['status']}{explanation}"
                raise ProgramFailure(message, meta=proc, outputs=outputs)

        finally:
            # Clean up the process from the agent.
            # FIXME
            # await self.__client.del_process(proc_id)
            pass


    def reconnect(self, run_id, run_state):
        log.debug(f"reconnect: {run_id}")
        return asyncio.ensure_future(self.wait(run_id, run_state))


    async def signal(self, run_id, run_state, signal):
        """
        :type signal:
          Signal name or number.
        """
        log.info(f"sending signal: {run_id}: {self.__timeout.signal}")
        proc_id = run_state["proc_id"]
        agent = self.__get_agent(run_state["host"])
        await agent.signal(proc_id, signal)



