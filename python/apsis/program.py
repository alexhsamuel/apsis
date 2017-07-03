import asyncio
from   functools import partial
import logging
from   pathlib import Path
import subprocess

log = logging.getLogger("program")

#-------------------------------------------------------------------------------

class ProcessProgram:

    def __init__(self, argv):
        self.__argv = tuple( str(a) for a in argv )
        self.__exec = Path(argv[0])


    async def run(self, run):
        log.info("running: {}".format(run))
        proc = await asyncio.create_subprocess_exec(
            *self.__argv, executable=self.__exec)
        log.info("proc: {}".format(proc))
        return_code = await proc.wait()
        log.info("return code: {}".format(return_code))


    def __call__(self, run):
        task = asyncio.ensure_future(self.run(run))
        log.info("task: {}".format(task))



