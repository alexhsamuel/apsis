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


    async def run(self, inst):
        log.info("running: {}".format(inst))
        proc = await asyncio.create_subprocess_exec(
            *self.__argv, executable=self.__exec)
        log.info("proc: {}".format(proc))
        return_code = await proc.wait()
        log.info("return code: {}".format(return_code))


    def __call__(self, inst):
        task = asyncio.ensure_future(self.run(inst))
        log.info("task: {}".format(task))



