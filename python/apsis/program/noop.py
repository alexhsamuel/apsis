import asyncio
import logging

from   .base import (Program, ProgramRunning, ProgramSuccess)
from   apsis.lib.json import check_schema
from   apsis.lib.parse import parse_duration
from   apsis.lib.py import or_none, nstr
from   apsis.runs import template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class NoOpProgram(Program):
    """
    A program that does nothing and always succeeds.
    """

    def __init__(self, *, duration=0):
        self.__duration = nstr(duration)


    def __str__(self):
        return "no-op" + (
            "" if self.__duration is None else f" for {self.__duration} s"
        )


    def bind(self, args):
        duration = or_none(template_expand)(self.__duration, args)
        return type(self)(duration=duration)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            duration = pop("duration", nstr, None)
        return cls(duration=duration)


    def to_jso(self):
        return {
            **super().to_jso(),
            "duration": self.__duration,
        }


    async def start(self, run_id, cfg):
        run_state = {}
        return ProgramRunning(run_state), self.wait(run_id, run_state)


    async def wait(self, run_id, run_state):
        if self.__duration is not None:
            duration = parse_duration(self.__duration)
            await asyncio.sleep(duration)
        return ProgramSuccess()


    def reconnect(self, run_id, run_state):
        return asyncio.ensure_future(self.wait(run_id, run_state))


    async def signal(self, run_state, signum):
        log.info("ignoring signal to no-op program")



