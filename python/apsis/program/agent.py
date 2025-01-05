import asyncio
import contextlib
import functools
import httpx
import logging
import ora
import socket
import traceback

from   .base import (
    Program, ProgramRunning, ProgramSuccess, ProgramFailure, ProgramError,
    program_outputs, Timeout, RunningProgram,
)
from   apsis.agent.client import Agent, NoSuchProcessError, HTTP_IMPL
from   apsis.host_group import expand_host
from   apsis.lib import memo
from   apsis.lib.cmpr import compress_async
from   apsis.lib.json import check_schema
from   apsis.lib.py import or_none, nstr
from   apsis.lib.sys import get_username
from   apsis.runs import template_expand, join_args

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

@functools.cache
def _get_agent(host, user):
    return Agent(host=host, user=user)


class AgentProgram(Program):

    def __init__(self, argv, *, host=None, user=None, timeout=None):
        self.argv = tuple( str(a) for a in argv )
        self.host = nstr(host)
        self.user = nstr(user)
        self.timeout = timeout


    def __str__(self):
        return join_args(self.argv)


    def bind(self, args):
        argv    = tuple( template_expand(a, args) for a in self.argv )
        host    = or_none(template_expand)(self.host, args)
        user    = or_none(template_expand)(self.user, args)
        timeout = None if self.timeout is None else self.timeout.bind(args)
        return type(self)(argv, host=host, user=user, timeout=timeout)


    def to_jso(self):
        jso = {
            **super().to_jso(),
            "argv"  : list(self.argv),
            "host"  : self.host,
            "user"  : self.user,
        }
        if self.timeout is not None:
            jso["timeout"] = self.timeout.to_jso()
        return jso


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv    = pop("argv")
            host    = pop("host", nstr, None)
            user    = pop("user", nstr, None)
            timeout = pop("timeout", Timeout.from_jso, None)
        return cls(argv, host=host, user=user, timeout=timeout)


    async def start(self, run_id, cfg):
        host = self.get_host(cfg)
        argv = self.argv

        loc = "" if host is None else " on " + host
        cmd = join_args(argv)
        log.debug(f"starting program{loc}: {cmd}")

        env = {
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
        if self.timeout is not None:
            try:
                start = ora.Time(run_state["start"])
            except KeyError:
                # Backward compatibility: no start in run state.
                # FIXME: Clean this up after transition.
                start = ora.now()

        explanation = ""

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1

        if HTTP_IMPL == "httpx":
            TIMEOUT = 60
            client_ctx = httpx.AsyncClient(
                verify=False,
                timeout=httpx.Timeout(TIMEOUT),
                limits=httpx.Limits(
                    max_keepalive_connections=1,
                    keepalive_expiry=TIMEOUT,
                ),
            )
        else:
            @contextlib.asynccontextmanager
            async def null_ctx():
                yield None

            client_ctx = null_ctx()

        async with client_ctx as client:
            while True:
                if self.timeout is not None:
                    elapsed = ora.now() - start
                    if self.timeout.duration < elapsed:
                        msg = f"timeout after {elapsed:.0f} s"
                        log.info(f"{run_id}: {msg}")
                        explanation = f" ({msg})"
                        # FIXME: Note timeout in run log.
                        await self.signal(run_id, run_state, self.timeout.signal)
                        await asyncio.sleep(POLL_INTERVAL)

                log.debug(f"polling proc: {run_id}: {proc_id} @ {host}")
                try:
                    proc = await agent.get_process(proc_id, restart=True, client=client)
                except NoSuchProcessError:
                    # Agent doesn't know about this process anymore.
                    raise ProgramError(f"program lost: {run_id}")
                if proc["state"] == "run":
                    await asyncio.sleep(POLL_INTERVAL)
                else:
                    break

            status = proc["status"]
            output, length, compression = await agent.get_process_output(proc_id, client=client)

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
                await agent.del_process(proc_id, client=client)


    def reconnect(self, run_id, run_state):
        log.debug(f"reconnect: {run_id}")
        return asyncio.ensure_future(self.wait(run_id, run_state))



class AgentShellProgram(AgentProgram):

    def __init__(self, command, **kw_args):
        command = str(command)
        argv = ["/bin/bash", "-c", command]
        super().__init__(argv, **kw_args)
        self.command = command


    def bind(self, args):
        command = template_expand(self.command, args)
        host    = or_none(template_expand)(self._AgentProgram__host, args)
        user    = or_none(template_expand)(self._AgentProgram__user, args)
        timeout = self._AgentProgram__timeout
        timeout = None if timeout is None else timeout.bind(args)
        return type(self)(command, host=host, user=user, timeout=timeout)


    def __str__(self):
        return self.command


    def to_jso(self):
        # A bit hacky.  Take the base-class JSO and replace argv with command.
        jso = super().to_jso()
        del jso["argv"]
        jso["command"] = self.command
        return jso


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            command = pop("command", str)
            host    = pop("host", nstr, None)
            user    = pop("user", nstr, None)
            timeout = pop("timeout", Timeout.from_jso, None)
        return cls(command, host=host, user=user, timeout=timeout)



#-------------------------------------------------------------------------------

class RunningAgentProgram(RunningProgram):

    def __init__(self, run_id, program, cfg, run_state=None):
        super().__init__(run_id)
        self.program    = program
        self.cfg        = cfg
        self.run_state  = run_state


    def __get_agent(self, host):
        host = None if host is None else socket.getfqdn(host)
        return _get_agent(host, self.user)


    @memo.property
    def updates(self):
        if self.run_state is None:
            host = expand_host(self.program.host, self.cfg)
            argv = self.program.argv

            loc = "" if host is None else " on " + host
            cmd = join_args(argv)
            log.debug(f"starting program{loc}: {cmd}")

            env = {
                "inherit": True,
                "vars": {
                    "APSIS_RUN_ID": self.run_id,
                },
            }

            meta = {
                "apsis_hostname"  : socket.gethostname(),
                "apsis_username"  : get_username(),
            }

            agent = self.__get_agent(host)
            proc = await agent.start_process(argv, env=env, restart=True)
            state = proc["state"]
            if state == "run":
                log.debug(f"program running: {self.run_id} as {proc['proc_id']}")

                start = ora.now()
                proc_id = proc["proc_id"]
                self.run_state = {
                    "host"          : host,
                    "proc_id"       : proc_id,
                    "pid"           : proc["pid"],
                    "start"         : str(start),
                }
                meta.update(self.run_state)
                # FIXME: Propagate times from agent.
                yield ProgramRunning(self.run_state, meta=meta)

            elif state == "err":
                message = proc.get("exception", "program error")
                log.info(f"program error: {self.run_id}: {message}")
                # Clean up the process from the agent.
                await agent.del_process(proc["proc_id"])

                yield ProgramError(message)
                return

            else:
                assert False, f"unknown state: {state}"

        else:
            proc = ...
            proc_id = self.run_state["proc_id"]
            start = ora.Time(self.run_state["start"])

        #------------

        explanation = ""

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1

        TIMEOUT = 60
        client_ctx = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(TIMEOUT),
            limits=httpx.Limits(
                max_keepalive_connections=1,
                keepalive_expiry=TIMEOUT,
            ),
        )

        async with client_ctx as client:
            while True:
                if self.timeout is not None:
                    elapsed = ora.now() - start
                    if self.timeout.duration < elapsed:
                        msg = f"timeout after {elapsed:.0f} s"
                        log.info(f"{self.run_id}: {msg}")
                        explanation = f" ({msg})"
                        # FIXME: Note timeout in run log.
                        await self.signal(self.run_id, self.run_state, self.timeout.signal)
                        await asyncio.sleep(POLL_INTERVAL)

                log.debug(f"polling proc: {self.run_id}: {proc_id} @ {host}")
                try:
                    proc = await agent.get_process(proc_id, restart=True, client=client)
                except NoSuchProcessError:
                    # Agent doesn't know about this process anymore.
                    raise ProgramError(f"program lost: {self.run_id}")
                if proc["state"] == "run":
                    await asyncio.sleep(POLL_INTERVAL)
                else:
                    break

            status = proc["status"]
            output, length, compression = await agent.get_process_output(proc_id, client=client)

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
                await agent.del_process(proc_id, client=client)

    async def signal(self, signal):
        """
        :type signal:
          Signal name or number.
        """
        if self.run_state is None:
            raise RuntimeError("can't signal; not running yet")

        log.info(f"sending signal: {self.run_id}: {signal}")
        proc_id = self.run_state["proc_id"]
        agent = self.__get_agent(self.run_state["host"])
        await agent.signal(proc_id, signal)


