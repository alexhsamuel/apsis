import asyncio
import heapq
import logging
from   ora import now

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------
# Helpers

async def soon(delay, coro):
    await asyncio.sleep(delay)
    await coro


#-------------------------------------------------------------------------------

class ScheduledRuns:
    """
    Scheduled runs waiting to execute.
    """

    # We maintain a time-ordered heap of scheduled runs, rather than using
    # the event loop, to guarantee that we are scheduling to the real time
    # clock, rather than the event loop's clock.
    #
    # The ready loop sleeps until the next scheduled job is ready, or for
    # MAX_DELAY, whichever comes first.  MAX_DELAY is important becayse event
    # loop clock may wander from the real time clock.  (This happens
    # dramatically if the computer sleeps.)  At most, the ready loop sleeps
    # for MAX_DELAY before rechecking the real time clock.

    MAX_DELAY = 1

    def __init__(self, start_run):
        """
        :param start_run:
          Async function that starts a run.
        """
        self.__start_run    = start_run
        self.__heap         = []

        # Get the ready loop started.
        self.__ready_task   = asyncio.ensure_future(self.__ready_loop())


    def __len__(self):
        return len(self.__heap)


    async def __ready_loop(self):
        while True:
            while len(self.__heap) > 0 and self.__heap[0][0] <= now():
                # The next run is ready.
                _, run = heapq.heappop(self.__heap)
                await self.__start_run(run)

            # Sleep until the next run is ready, or MAX_DELAY.
            await asyncio.sleep(
                self.MAX_DELAY if len(self.__heap) == 0
                else min(self.MAX_DELAY, self.__heap[0][0] - now())
            )


    def schedule(self, time, run):
        wait = time - now()
        if wait <= 0:
            # Job is ready; run it now.
            log.info(f"run immediately: {time} {run.run_id}")
            asyncio.ensure_future(self.__start_run(run))

        elif wait <= self.MAX_DELAY:
            # Job is almost ready; use the event loop, sine the ready loop may
            # be sleeping for a while.  
            # FIXME: Runs scheduled this way can't be unscheduled.
            log.info(f"run soon: {time} {run.run_id}")
            asyncio.ensure_future(soon(wait, self.__start_run(run)))

        else:
            # Put it onto the schedule heap.
            log.info(f"schedule: {time} {run.run_id}")
            heapq.heappush(self.__heap, (time, run))


    def unschedule(self, run):
        log.info(f"unschedule: {run}")
        # FIXME: This is horrible.  Figure out a better way.
        self.__heap = [ (t, r) for t, r in self.__heap if r is not run ]
        heapq.heapify(self.__heap)



