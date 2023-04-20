import asyncio
import functools
import logging
import socket
import traceback

from   .base import (
    Program, ProgramRunning, ProgramSuccess, ProgramFailure, ProgramError,
    program_outputs
)
from   apsis.agent.client import Agent, NoSuchProcessError
from   apsis.host_group import expand_host
from   apsis.lib.cmpr import compress_async
from   apsis.lib.json import check_schema
from   apsis.lib.py import or_none, nstr
from   apsis.lib.sys import get_username
from   apsis.runs import template_expand, join_args

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _get_agent(fqdn, user):
    return Agent(host=fqdn, user=user)


class AgentProgram(Program):

    def __init__(self, argv, *, host=None, user=None):
        self.__argv = tuple( str(a) for a in argv )
        self.__host = nstr(host)
        self.__user = nstr(user)


    def __str__(self):
        return join_args(self.__argv)


    def __get_agent(self, host):
        host = None if host is None else socket.getfqdn(host)
        return _get_agent(host, self.__user)


    def bind(self, args):
        argv = tuple( template_expand(a, args) for a in self.__argv )
        host = or_none(template_expand)(self.__host, args)
        user = or_none(template_expand)(self.__user, args)
        return type(self)(argv, host=host, user=user)


    def to_jso(self):
        return {
            **super().to_jso(),
            "argv"      : list(self.__argv),
            "host"      : self.__host,
            "user"      : self.__user,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv    = pop("argv")
            host    = pop("host", nstr, None)
            user    = pop("user", nstr, None)
        return cls(argv, host=host, user=user)


    def get_host(self, cfg):
        return expand_host(self.__host, cfg)


    async def start(self, run_id, cfg):
        host = self.get_host(cfg)
        argv = self.__argv

        loc = "" if host is None else " on " + host
        cmd = join_args(argv)
        log.info(f"starting program{loc}: {cmd}")

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
            log.info(f"program running: {run_id} as {proc['proc_id']}")

            run_state = {
                "host"          : host,
                "proc_id"       : proc["proc_id"],
                "pid"           : proc["pid"],
            }
            meta.update(run_state)
            # FIXME: Propagate times from agent.
            # FIXME: Do this asynchronously from the agent instead.
            done = self.wait(run_id, run_state)
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

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1
        while True:
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
        log.info(f"got output: {length} bytes, {compression or 'uncompressed'}")

        try:
            if status == 0:
                log.info(f"program success: {run_id}")
                return ProgramSuccess(meta=proc, outputs=outputs)

            else:
                message = f"program failed: status {status}"
                log.info(f"program failed: {run_id}: {message}")
                raise ProgramFailure(message, meta=proc, outputs=outputs)

        finally:
            # Clean up the process from the agent.
            await agent.del_process(proc_id)


    def reconnect(self, run_id, run_state):
        log.info(f"reconnect: {run_id}")
        return asyncio.ensure_future(self.wait(run_id, run_state))


    async def signal(self, run_state, signum):
        proc_id = run_state["proc_id"]
        agent = self.__get_agent(run_state["host"])
        await agent.signal(proc_id, signum)



class AgentShellProgram(AgentProgram):

    def __init__(self, command, **kw_args):
        command = str(command)
        argv = ["/bin/bash", "-c", command]
        super().__init__(argv, **kw_args)
        self.__command = command


    def bind(self, args):
        command = template_expand(self.__command, args)
        host = or_none(template_expand)(self._AgentProgram__host, args)
        user = or_none(template_expand)(self._AgentProgram__user, args)
        return type(self)(command, host=host, user=user)


    def __str__(self):
        return self.__command


    def to_jso(self):
        jso = super().to_jso()
        del jso["argv"]
        jso["command"] = self.__command
        return jso


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            command = pop("command", str)
            host    = pop("host", nstr, None)
            user    = pop("user", nstr, None)
        return cls(command, host=host, user=user)



