import asyncio
import getpass
import jinja2
import logging
from   pathlib import Path
import shlex
import socket

from   .types import ProgramError, ProgramFailure
from   .agent.client import Agent

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def template_expand(template, args):
    return jinja2.Template(template).render(args)


def join_args(argv):
    return " ".join( shlex.quote(a) for a in argv )


#-------------------------------------------------------------------------------

class ShellMixin:

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


    async def start(self, run):
        argv = self.__argv
        log.info(f"starting: {join_args(argv)}")

        run.meta.update({
            "command"   : " ".join( shlex.quote(a) for a in argv ),
            "hostname"  : socket.gethostname(),
            "username"  : getpass.getuser(),
        })

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
            raise ProgramError(str(exc))
        else:
            run.meta["pid"] = proc.pid
            return proc


    async def wait(self, run, proc):
        stdout, stderr  = await proc.communicate()
        return_code     = proc.returncode

        assert stderr is None
        assert return_code is not None

        run.meta["return_code"] = return_code
        run.output = stdout
        log.info(f"complete with return code {return_code}")
        if return_code == 0:
            return
        else:
            raise ProgramFailure("return code = {}".format(return_code))



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
        log.info(f"starting: {join_args(argv)}")

        run.meta.update({
            "command"   : " ".join( shlex.quote(a) for a in argv ),
            "hostname"  : socket.gethostname(),
            "username"  : getpass.getuser(),
        })

        process = await self.__agent.start_process(argv)
        state   = process["state"]
        if state == "run":
            run.meta["proc_id"] = process["proc_id"]
            run.meta["pid"] = process["pid"]
            return process
        elif state == "err":
            raise ProgramError(process.get("exception", "program error"))
        else:
            assert False, f"unknown state: {state}"
        

    async def wait(self, run, proc):
        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1

        proc_id = proc["proc_id"]
        while True:
            log.debug(f"polling proc: {proc_id}")
            proc = await self.__agent.get_process(proc_id)
            if proc["state"] == "run":
                await asyncio.sleep(POLL_INTERVAL)
            else:
                break

        run.meta["return_code"] = status = proc["status"]  # FIXME: Translate?
        run.output = await self.__agent.get_process_output(proc_id)
        await self.__agent.del_process(proc_id)
        if status == 0:
            return
        else:
            raise ProgramFailure(f"program failed: status {status}")



class AgentShellProgram(ShellMixin, AgentProgram):

    pass



