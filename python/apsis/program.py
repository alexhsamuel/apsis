import asyncio
import getpass
import jinja2
import logging
from   pathlib import Path
import shlex
import socket

from   .agent.client import Agent

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def template_expand(template, args):
    return jinja2.Template(template).render(args)


def join_args(argv):
    return " ".join( shlex.quote(a) for a in argv )


#-------------------------------------------------------------------------------

class Program:

    def bind(self, args):
        """
        Returns a new program with parameters bound to `args`.
        """


    async def start(self, run, update_run):
        """
        Starts the run.

        Updates `run` in place.

        :param run:
          The run to run.
        :param update_run:
          Coro to update run state.
        :postcondition:
          The run state is "running" or "error".
        """



#-------------------------------------------------------------------------------

class ShellMixin:
    # Note: This mixin must precede the main program class in bases, as its
    # __init__ needs to go first.

    def __init__(self, command, **kw_args):
        # FIXME: Which shell?
        command = str(command)
        argv = ["/bin/bash", "-c", command]
        super().__init__(argv, **kw_args)
        self.__command = command


    def bind(self, args):
        command = template_expand(self.__command, args)
        return type(self)(command)


    def __str__(self):
        return self.__command



#-------------------------------------------------------------------------------

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%kZ"

class ProcessProgram:

    def __init__(self, argv):
        self.__argv = tuple( str(a) for a in argv )


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv = tuple( template_expand(a, args) for a in self.__argv )
        return type(self)(argv)


    def to_jso(self):
        return {
            "argv"      : list(self.__argv),
        }


    async def start(self, run, update_run):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        meta = {
            "command"   : " ".join( shlex.quote(a) for a in argv ),
            "hostname"  : socket.gethostname(),
            "username"  : getpass.getuser(),
        }

        try:
            with open("/dev/null") as stdin:
                proc = await asyncio.create_subprocess_exec(
                    *argv, 
                    executable  =Path(argv[0]),
                    stdin       =stdin,
                    # Merge stderr with stdin.  FIXME: Do better.
                    stdout      =asyncio.subprocess.PIPE,
                    stderr      =asyncio.subprocess.STDOUT,
                )

        except OSError as exc:
            # Error starting.
            run.set_error(str(exc), meta)
            await update_run(run)

        else:
            # Started successfully.
            run.set_running(meta={"pid": proc.pid, **meta})
            await update_run(run)
            await self.wait(run, proc, update_run)


    async def wait(self, run, proc, update_run):
        stdout, stderr  = await proc.communicate()
        return_code     = proc.returncode
        log.info(f"complete with return code {return_code}")
        meta = {
            "return_code": return_code,
        }

        assert stderr is None
        assert return_code is not None

        if return_code == 0:
            run.set_success(stdout, meta)
        else:
            run.set_failure(f"program failed: status {return_code}", stdout, meta)
        await update_run(run)



class ShellCommandProgram(ShellMixin, ProcessProgram):

    pass



#-------------------------------------------------------------------------------

class AgentProgram:

    def __init__(self, argv):
        self.__argv = tuple( str(a) for a in argv )
        self.__agent = Agent()


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv = tuple( template_expand(a, args) for a in self.__argv )
        return type(self)(argv)


    def to_jso(self):
        return {
            "argv"      : list(self.__argv),
        }


    async def start(self, run):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        # FIXME: Factor out, or move to agent.
        meta = {
            "command"   : " ".join( shlex.quote(a) for a in argv ),
            "hostname"  : socket.gethostname(),
            "username"  : getpass.getuser(),
        }

        proc = await self.__agent.start_process(argv)

        state = proc["state"]
        if state == "run":
            log.info(f"program running: {run.run_id} as {proc['proc_id']}")

            run_state = {
                "proc_id"   : proc["proc_id"],
                "pid"       : proc["pid"],
            }
            # FIXME: Propagate times from agent.
            run.to_running(run_state, meta=meta)

            # FIXME: Do this asynchronously from the agent instead.
            await self.wait(run)

        elif state == "err":
            message = proc.get("exception", "program error")
            log.info(f"program error: {run.run_id}: {message}")
            run.to_error(message, meta=meta)

        else:
            assert False, f"unknown state: {state}"


    async def wait(self, run):
        proc_id = run.run_state["proc_id"]

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1
        while True:
            log.debug(f"polling proc: {proc_id}")
            proc = await self.__agent.get_process(proc_id)
            if proc["state"] == "run":
                await asyncio.sleep(POLL_INTERVAL)
            else:
                break

        status = proc["status"]
        meta = {
            "return_code"   : status,
        }            
        output = await self.__agent.get_process_output(proc_id)

        if status == 0:
            log.info(f"program success: {run.run_id}")
            run.to_success(output=output, meta=meta)
        else:
            message = f"program failed: status {status}"
            log.info(f"program failed: {run.run_id}: {message}")
            run.to_failure(message, output=output, meta=meta)

        # Clean up the process from the agent.
        await self.__agent.del_process(proc_id)


    def reconnect(self, run):
        log.info(f"reconnect: {run.run_id}")
        asyncio.ensure_future(self.wait(run))


                                        
class AgentShellProgram(ShellMixin, AgentProgram):

    pass



