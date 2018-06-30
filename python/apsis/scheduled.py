import asyncio
import logging
from   ora import now

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------
# Helpers

def at(time, coro):
    async def delayed():
        delay = time - now()
        if delay > 0:
            # FIXME: Maybe we shouldn't sleep all at once, so we can cancel
            # this without waiting for the schedule time?
            await asyncio.sleep(delay)
        await coro
    return asyncio.ensure_future(delayed())


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
        task = at(time, self.__ready(run))
        self.__runs[run] = task


    def unschedule(self, run):
        log.info(f"unschedule: {run}")
        task = self.__runs.pop(run)
        task.cancel()



