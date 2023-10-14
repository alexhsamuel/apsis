"""
Action types for testing.
"""

import logging

from   .base import BaseAction, ThreadAction
from   .condition import Condition
from   apsis.lib import py
from   apsis.lib.json import check_schema

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class SleepThreadAction(ThreadAction):
    """
    Action that (blocking) sleeps.
    """

    def __init__(self, duration, *, condition=None):
        super().__init__(condition=condition)
        self.__duration = duration


    def __repr__(self):
        return py.format_ctor(self, self.__duration, condition=self.condition)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            condition   = pop("if", Condition.from_jso, None)
            duration    = pop("duration", float)
        return cls(duration, condition=condition)


    def to_jso(self):
        return {
            **super().to_jso(),
            "duration"  : self.__duration,
        }


    def run(self, run):
        import time

        # Blocking actions are OK here.
        log.info(f"sleeping action for {self.__duration} s")
        time.sleep(self.__duration)
        log.info("sleeping action done")



class ErrorThreadAction(ThreadAction):
    """
    Thread action that raises an exception.
    """

    def run(self, run):
        log.info("error action")
        raise RuntimeError("something went wrong")


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            condition   = pop("if", Condition.from_jso, None)
        return cls(condition=condition)



class LogAction(BaseAction):
    """
    Action that dumps out contents of the run snapshot.
    """

    async def __call__(self, apsis, run):
        log.info(f"run ID: {run.run_id}")
        log.info(f"run: {run}")
        log.info(f"job: {run.job}")
        log.info(f"output: {run.outputs['output'].get_uncompressed_data().decode()}")


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            condition   = pop("if", Condition.from_jso, None)
        return cls(condition=condition)



