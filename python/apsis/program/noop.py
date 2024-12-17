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

    def __init__(self, *, duration=0, success=True):
        self.__duration = nstr(duration)
        self.__success  = nbool(success)


    def __str__(self):
        return "no-op" + (
            "" if self.__duration is None else f" for {self.__duration} s"
        )


    def bind(self, args):
        duration = or_none(template_expand)(self.__duration, args)
        return BoundNoOpProgram(duration=duration, success=self.__success)


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



#-------------------------------------------------------------------------------

class BoundNoOpProgram(Program):
    """
    A program that does nothing.

    `duration` is the time it takes the program to run.  If `success` is true,
    the program always succeeds; if false, it fails; if none, it errors.
    """

    __stop_events = {}

    def __init__(self, *, duration=0, success=True):
        self.__duration = nstr(duration)
        self.__success = None if success is None else bool(success)


    def __str__(self):
        return "no-op" + (
            "" if self.__duration is None else f" for {self.__duration} s"
        )


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


    async def run(self, run_id, cfg):
        run_state = {"run_id": run_id}
        yield ProgramRunning(run_state)
        async for update in self.wait(run_state):
            yield update


    async def wait(self, run_state):
        if self.__duration is not None:
            run_id = run_state["run_id"]
            duration = parse_duration(self.__duration)
            stop_event = self.__stop_events[run_id] = asyncio.Event()
            try:
                await asyncio.wait_for(stop_event.wait(), duration)
            except asyncio.TimeoutError:
                # OK, duration expired.
                pass
            else:
                yield ProgramError("program stopped")
                return
            finally:
                assert self.__stop_events.pop(run_id) == stop_event

        if self.__success is True:
            yield ProgramSuccess()
        elif self.__success is False:
            yield ProgramFailure("failed")
        else:
            yield ProgramError("error")


    def connect(self, run_id, run_state):
        return self.wait(run_state)


    async def signal(self, run_id, run_state, signal):
        log.info("ignoring signal to no-op program")


    async def stop(self, run_state):
        run_id = run_state["run_id"]
        stop_event = self.__stop_events[run_id]
        stop_event.set()



