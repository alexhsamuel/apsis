import asyncio
import functools
import logging
import os
from   pathlib import Path
import pwd
import socket
import traceback

from   .agent.client import Agent, NoSuchProcessError
from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import or_none
from   .runs import template_expand, join_args

log = logging.getLogger(__name__)

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


    # FIXME: Find a better way to get run_id into logging without passing it in.

    async def start(self, run_id):
        """
        Starts the run.

        Updates `run` in place.

        :param run_id:
          The run ID; used for logging only.
        :raise ProgramError:
          The program failed to start.
        :return:
          `running, done`, where `running` is a `ProgramRunning` instance and
          `done` is a coroutine or future that returns `ProgramSuccess` when the
          program is complete.
        """


    def reconnect(self, run_id, run_state):
        """
        Reconnects to an already running run.

        :param run_id:
          The run ID; used for logging only.
        :param run_state:
          State information for the running program.
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


    async def start(self, run_id):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        meta = {
            "hostname"  : socket.gethostname(),
            "username"  : pwd.getpwuid(os.getuid()).pw_name,
            "euid"      : pwd.getpwuid(os.geteuid()).pw_name,
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
            done = self.wait(run_id, proc)
            return ProgramRunning({"pid": proc.pid}, meta=meta), done


    async def wait(self, run_id, proc):
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
            message = f"program failed: return code {return_code}"
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

@functools.lru_cache(maxsize=None)
def _get_agent(host, user):
    return Agent(host=host, user=user)


class AgentProgram:

    def __init__(self, argv, *, host=None, user=None):
        self.__argv = tuple( str(a) for a in argv )
        self.__host = or_none(str)(host)
        self.__user = or_none(str)(user)


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv = tuple( template_expand(a, args) for a in self.__argv )
        host = or_none(template_expand)(self.__host, args)
        user = or_none(template_expand)(self.__user, args)
        return type(self)(argv, host=host, user=user)


    def to_jso(self):
        return {
            "argv"      : list(self.__argv),
            "host"      : self.__host,
            "user"      : self.__user,
        }


    @classmethod
    def from_jso(Class, jso):
        return Class(
            jso.pop("argv"), 
            host=jso.pop("host", None),
            user=jso.pop("user", None),
        )


    def __get_agent(self):
        return _get_agent(self.__host, self.__user)


    async def start(self, run_id):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        meta = {
            "apsis_hostname"  : socket.gethostname(),
            "apsis_username"  : pwd.getpwuid(os.getuid()).pw_name,
        }

        try:
            agent = self.__get_agent()
            proc = await agent.start_process(argv, restart=True)

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
        proc_id = run_state["proc_id"]
        agent = self.__get_agent()

        # FIXME: This is so embarrassing.
        POLL_INTERVAL = 1
        while True:
            log.debug(f"polling proc: {proc_id}")
            try:
                proc = await agent.get_process(proc_id, restart=True)
            except NoSuchProcessError:
                # Agent doens't know about this process anymore.
                raise ProgramError(f"program lost: {run_id}")
            if proc["state"] == "run":
                await asyncio.sleep(POLL_INTERVAL)
            else:
                break

        status = proc["status"]
        output = await agent.get_process_output(proc_id)
        outputs = program_outputs(output)

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
    def from_jso(Class, jso):
        return Class(
            jso.pop("command"),
            host=jso.pop("host", None),
            user=jso.pop("user", None),
        )



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

