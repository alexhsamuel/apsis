import asyncio
import logging

from   .base import (
    Program, ProgramRunning, ProgramSuccess, ProgramFailure, ProgramError)
from   apsis.lib.json import check_schema
from   apsis.lib.parse import parse_duration
from   apsis.lib.py import or_none, nstr, nbool
from   apsis.runs import template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class NoOpProgram(Program):
    """
    A program that does nothing.

    `duration` is the time it takes the program to run.  If `success` is true,
    the program always succeeds; if false, it fails; if none, it errors.
    """

    def __init__(self, *, duration=0, success=True):
        self.__duration = nstr(duration)
        self.__success = None if success is None else bool(success)
        # For signaling stop.
        self.__stop_queue = asyncio.Event()


    def __str__(self):
        return "no-op" + (
            "" if self.__duration is None else f" for {self.__duration} s"
        )


    def bind(self, args):
        duration = or_none(template_expand)(self.__duration, args)
        return type(self)(duration=duration, success=self.__success)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            duration    = pop("duration", nstr, None)
            success     = pop("success", nbool, True)
        return cls(duration=duration, success=success)


    def to_jso(self):
        return {
            **super().to_jso(),
            "duration"  : self.__duration,
            "success"   : self.__success,
        }


    async def start(self, run_id, cfg):
        run_state = {}
        return ProgramRunning(run_state), self.wait(run_id, run_state)


    async def wait(self, run_id, run_state):
        if self.__duration is not None:
            duration = parse_duration(self.__duration)
            try:
                await asyncio.wait_for(self.__stop_queue.wait(), duration)
            except asyncio.TimeoutError:
                # OK, duration expired.
                pass
            else:
                raise ProgramError("program stopped")
        if self.__success is True:
            return ProgramSuccess()
        elif self.__success is False:
            raise ProgramFailure("failed")
        else:
            raise ProgramError("error")


    def reconnect(self, run_id, run_state):
        return asyncio.ensure_future(self.wait(run_id, run_state))


    async def signal(self, run_state, signum):
        log.info("ignoring signal to no-op program")


    async def stop(self):
        self.__stop_queue.set()



