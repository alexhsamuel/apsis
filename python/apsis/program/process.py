import asyncio
import logging
import os
from   pathlib import Path
import pwd
import socket

from   .base import (
    Program, ProgramRunning, ProgramSuccess, ProgramFailure, ProgramError,
    program_outputs
)
from   apsis.lib.sys import get_username
from   apsis.runs import template_expand, join_args

log = logging.getLogger(__name__)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%kZ"

#-------------------------------------------------------------------------------

class ProcessProgram(Program):

    def __init__(self, argv):
        self.__argv = tuple( str(a) for a in argv )


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv = tuple( template_expand(a, args) for a in self.__argv )
        return type(self)(argv)


    def to_jso(self):
        return {
            **super().to_jso(),
            "argv"      : list(self.__argv),
        }


    @classmethod
    def from_jso(cls, jso):
        return cls(jso["argv"])


    async def start(self, run_id, cfg):
        argv = self.__argv
        log.info(f"starting program: {join_args(argv)}")

        meta = {
            "hostname"  : socket.gethostname(),
            "username"  : get_username(),
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


    async def signal(self, run_id, signum: str):
        # FIXME
        raise NotImplementedError()



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
            **Program.to_jso(self),
            "command"   : self.__command,
        }


    @classmethod
    def from_jso(cls, jso):
        return cls(jso["command"])



