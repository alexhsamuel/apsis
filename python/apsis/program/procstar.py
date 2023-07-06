import asyncio
import logging
import ora
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


    async def start(self, run_id, cfg):
        # FIXME: expand_host() should probably act on addres, not hosts.
        addr = NetAddress(expand_host(self.__addr.host, cfg), self.__addr.port)
        argv = self.__argv

        log.debug(f"starting program at {addr}: {join_args(argv)}")

        # FIXME: env.
        _env = {
            "inherit": True,
            "vars": {
                "APSIS_RUN_ID": run_id,
                # FIXME: Other things?
            },
        }
        meta = {
            "apsis_hostname"  : socket.gethostname(),
            "apsis_username"  : get_username(),
        }

        try:
            agent = self.__get_agent(host)
            proc = await agent.start_process(argv, env=env, restart=True)

        except Exception as exc:
            log.error("failed to start process", exc_info=True)
            output = traceback.format_exc().encode()
            # FIXME: Use a different "traceback" output, once the UI can
            # understand it.
            raise ProgramError(
                message=str(exc), outputs=program_outputs(output))

        state = proc["state"]
        if state == "run":
            log.debug(f"program running: {run_id} as {proc['proc_id']}")

            run_state = {
                "host"          : host,
                "proc_id"       : proc["proc_id"],
                "pid"           : proc["pid"],
            }
            meta.update(run_state)
            # FIXME: Propagate times from agent.
            # FIXME: Do this asynchronously from the agent instead.
            done = self.wait(run_id, run_state)
            run_state["start"] = str(ora.now())
            return ProgramRunning(run_state, meta=meta), done

        elif state == "err":
            message = proc.get("exception", "program error")
            log.info(f"program error: {run_id}: {message}")
            # Clean up the process from the agent.
            await agent.del_process(proc["proc_id"])

            raise ProgramError(message)

        else:
            assert False, f"unknown state: {state}"


    async def wait(self, run_id, run_state):
        host = run_state["host"]
        proc_id = run_state["proc_id"]
        agent = self.__get_agent(host)
        if self.__timeout is not None:
            try:
                start = ora.Time(run_state["start"])
            except KeyError:
                # Backward compatibility: no start in run state.
                # FIXME: Clean this up after transition.
                start = ora.now()

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

            log.debug(f"polling proc: {run_id}: {proc_id} @ {host}")
            try:
                proc = await agent.get_process(proc_id, restart=True)
            except NoSuchProcessError:
                # Agent doesn't know about this process anymore.
                raise ProgramError(f"program lost: {run_id}")
            if proc["state"] == "run":
                await asyncio.sleep(POLL_INTERVAL)
            else:
                break

        status = proc["status"]
        output, length, compression = await agent.get_process_output(proc_id)

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
            if status == 0:
                return ProgramSuccess(meta=proc, outputs=outputs)

            else:
                message = f"program failed: status {status}{explanation}"
                raise ProgramFailure(message, meta=proc, outputs=outputs)

        finally:
            # Clean up the process from the agent.
            await agent.del_process(proc_id)


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



