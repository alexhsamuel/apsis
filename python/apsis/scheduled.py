import asyncio
import logging
from   ora import now

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------
# Helpers

def at(time, coro):
    return asyncio.get_event_loop().call_later(
        time - now(), lambda: asyncio.ensure_future(coro()))


#-------------------------------------------------------------------------------

class ScheduledRuns:
    """
    Scheduled runs waiting to execute.
    """

    def __init__(self, start_run):
        self.__start_run    = start_run
        self.__runs         = {}


    def __len__(self):
        return len(self.__runs)


    async def __ready(self, run):
        # Clean up the task.
        del self.__runs[run]
        # Get going.
        await self.__start_run(run)


    def schedule(self, time, run):
        log.info(f"schedule: {time} {run.run_id}")
        task = at(time, lambda: self.__ready(run))
        self.__runs[run] = task


    def unschedule(self, run):
        log.info(f"unschedule: {run}")
        task = self.__runs.pop(run)
        task.cancel()


