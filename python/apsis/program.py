import asyncio
import getpass
import jinja2
import logging
from   pathlib import Path
import shlex
import socket

from   .agent.client import Agent
from   .lib.json import Typed, no_unexpected_keys

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def template_expand(template, args):
    return jinja2.Template(template).render(args)


def join_args(argv):
    return " ".join( shlex.quote(a) for a in argv )


#-------------------------------------------------------------------------------

class OutputMetadata:

    def __init__(self, name: str, length: int, *, 
                 content_type="application/octet-stream"):
        """
        :param name:
          User-visible output name.
        :param length:
          Length in bytes.
        :param content_type:
          MIME type of output.
        """
        self.name           = str(name)
        self.length         = len(self.data) if length is None else int(length)
        self.content_type   = str(content_type)



class Output:

    def __init__(self, metadata: OutputMetadata, data: bytes, compression=None):
        """
        :param metadata:
          Information about the data.
        :param data:
          The data bytes.
        :pamam compression:
          The compresison type, or `None` for uncompressed.
        """
        self.metadata       = metadata
        self.data           = data
        self.compression    = None
    


def program_outputs(output: bytes):
    return {
        "output": Output(
            OutputMetadata("combined stdout & stderr", length=len(output)),
            output
        ),
    }


#-------------------------------------------------------------------------------

class ProgramRunning:

    def __init__(self, run_state, *, meta={}, times={}):
        self.run_state  = run_state
        self.meta       = meta
        self.times      = times



class ProgramError(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs



class ProgramSuccess:

    def __init__(self, *, meta={}, times={}, outputs={}):
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs
    


class ProgramFailure(RuntimeError):

    def __init__(self, message, *, meta={}, times={}, outputs={}):
        self.message    = message
        self.meta       = meta
        self.times      = times
        self.outputs    = outputs



class Program:

    def bind(self, args):
        """
        Returns a new program with parameters bound to `args`.
        """


    async def start(self, run):
        """
        Starts the run.

        Updates `run` in place.

        :param run:
          The run to run.
        :raise ProgramError:
          The program failed to start.
        :return:
          `running, done`, where `running` is a `ProgramRunning` instance and
          `done` is a coroutine or future that returns `ProgramSuccess` when the
          program is complete.
        """


    def reconnect(self, run):
        """
        Reconnects to an already running run.

        :return:
          A coroutine or future for the program completion, as `start`.
        """



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


    @classmethod
    def from_jso(Class, jso):
        return Class(jso["argv"])


    async def start(self, run):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        meta = {
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
            raise ProgramError(str(exc), meta=meta)

        else:
            # Started successfully.
            done = self.wait(run, proc)
            return ProgramRunning({"pid": proc.pid}, meta=meta), done


    async def wait(self, run, proc):
        stdout, stderr  = await proc.communicate()
        return_code     = proc.returncode
        log.info(f"complete with return code {return_code}")
        assert stderr is None
        assert return_code is not None

        meta = {
            "return_code": return_code,
        }
        outputs = program_outputs(stdout)

        if return_code == 0:
            return ProgramSuccess(meta=meta, outputs=outputs)

        else:
            message = f"program failed: status {return_code}"
            raise ProgramFailure(message, meta=meta, outputs=outputs)



class ShellCommandProgram(ProcessProgram):

    def __init__(self, command):
        command = str(command)
        argv = ["/bin/bash", "-c", command]
        super().__init__(argv)
        self.__command = command


    def bind(self, args):
        command = template_expand(self.__command, args)
        return type(self)(command)


    def __str__(self):
        return self.__command


    def to_jso(self):
        return {
            "command"   : self.__command,
        }


    @classmethod
    def from_jso(Class, jso):
        return Class(jso["command"])



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


    @classmethod
    def from_jso(Class, jso):
        return Class(jso.pop("argv"))


    async def start(self, run):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        # FIXME: Factor out, or move to agent.
        meta = {
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
            # FIXME: Do this asynchronously from the agent instead.
            done = self.wait(run)
            return ProgramRunning(run_state, meta=meta), done

        elif state == "err":
            message = proc.get("exception", "program error")
            log.info(f"program error: {run.run_id}: {message}")
            raise ProgramError(message)

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

        # FIXME: Is it "status" or is it "return code"?
        status = proc["status"]
        meta = {
            "return_code": status,
        }            
        output = await self.__agent.get_process_output(proc_id)
        outputs = program_outputs(output)

        try:
            if status == 0:
                log.info(f"program success: {run.run_id}")
                return ProgramSuccess(meta=meta, outputs=outputs)

            else:
                message = f"program failed: status {status}"
                log.info(f"program failed: {run.run_id}: {message}")
                raise ProgramFailure(message, meta=meta, outputs=outputs)

        finally:
            # Clean up the process from the agent.
            await self.__agent.del_process(proc_id)


    def reconnect(self, run):
        log.info(f"reconnect: {run.run_id}")
        return asyncio.ensure_future(self.wait(run))


                                        
class AgentShellProgram(AgentProgram):

    def __init__(self, command):
        command = str(command)
        argv = ["/bin/bash", "-c", command]
        super().__init__(argv)
        self.__command = command


    def bind(self, args):
        command = template_expand(self.__command, args)
        return type(self)(command)


    def __str__(self):
        return self.__command


    def to_jso(self):
        return {
            "command": self.__command,
        }


    @classmethod
    def from_jso(Class, jso):
        return Class(jso.pop("command"))



#-------------------------------------------------------------------------------

TYPES = Typed({
    "program"       : AgentProgram,
    "shell"         : AgentShellProgram,
    "program_inproc": ProcessProgram,
    "shell_inproc"  : ShellCommandProgram,
})


def program_from_jso(jso):
    if isinstance(jso, str):
        return AgentShellProgram(jso)
    elif isinstance(jso, list):
        return AgentProgram(jso)
    else:
        with no_unexpected_keys(jso):
            return TYPES.from_jso(jso)


program_to_jso = TYPES.to_jso

