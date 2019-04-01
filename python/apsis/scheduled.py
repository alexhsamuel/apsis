import asyncio
import heapq
import logging
from   ora import now, Time

from   .runs import Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

async def sleep_until(time):
    """
    Sleep until `time`, or do our best at least.
    """
    delay = time - now()

    # FIXME: These thresholds are rather ad hoc.

    if delay <= 0:
        # Nothing to do.
        if delay < 0.1:
            log.debug(f"sleep to past time: {time}")

    else:
        await asyncio.sleep(delay)
        late = now() - time
        if late < -0.005:
            log.error(f"woke up early: {-late:.3f} s")
        elif late > 0.1:
            log.error(f"woke up late: {late:.1f} s")


class ScheduledRuns:
    """
    Scheduled runs waiting to start.
    """

    # We maintain an explicit run schedule, rather than using the event loop, to
    # guarantee that we are scheduling to the real time clock, rather than the
    # event loop's clock.

    # Max delay time.  Generally, a run is started very close to its scheduled
    # time, but in some cases the run may be delayed as much as this time.

    LOOP_TIME = 1

    # Entry is the data structure stored in __heap.  It represents a scheduled
    # run.  We also maintain __scheduled, a map from Run to Entry, to find an
    # entry of an already-scheduled job.
    #
    # Since an entry cannot easily be removed from the middle of a heap, we
    # unschedule a job by setting scheduled=False.  It stays in the heap, but
    # we ignore it when it comes to to top.  However, __scheduled only includes
    # entries for which scheduled==True.

    class Entry:

        def __init__(self, time, run):
            self.time = time
            self.run = run
            self.scheduled = True

        def __hash__(self):
            return hash(self.time)

        def __eq__(self, other):
            return self.time == other.time

        def __lt__(self, other):
            return self.time < other.time



    def __init__(self, clock_db, start_run):
        """
        :param clock_db:
          Persistence for most recent scheduled time.
        :param start_run:
          Async function that starts a run.
        """
        self.__clock_db     = clock_db
        self.__start_run    = start_run

        # Heap of Entry, ordered by schedule time.  The top entry is the next
        # scheduled run.
        self.__heap         = []

        # Mapping from Run to Entry.  Values satisfy entry.scheduled==True.
        self.__scheduled    = {}


    def __len__(self):
        return len(self.__heap)


    async def loop(self):
        # The start loop sleeps until the time to start the next scheduled job,
        # or for LOOP_TIME, whichever comes first.  LOOP_TIME comes in to play
        # when the event loop clock wanders from the real time clock, or if a
        # run is scheduled in the very near future after the start loop has
        # already gone to sleep.
        try:
            log_next_time = None

            while True:
                time = now()

                if log.isEnabledFor(logging.DEBUG):
                    count = len(self.__heap)
                    next_time = None if count == 0 else self.__heap[0].time
                    if next_time != log_next_time:
                        next_run = "none" if count == 0 else self.__heap[0].run.run_id
                        log.debug(f"loop: {count} scheduled runs; next {next_run} at {next_time}")
                        log_next_time = next_time

                ready = set()
                while len(self.__heap) > 0 and self.__heap[0].time <= time:
                    # The next run is ready.
                    entry = heapq.heappop(self.__heap)
                    if entry.scheduled:
                        # Take it out of the entries dict.
                        assert self.__scheduled.pop(entry.run) is entry
                        ready.add(entry.run)
                self.__clock_db.set_time(time)

                if len(ready) > 0:
                    log.debug(f"{len(ready)} runs ready")
                    # Start the runs.
                    # FIXME: Return exceptions?
                    await asyncio.gather(*( self.__start_run(r) for r in ready ))

                next_time = time + self.LOOP_TIME
                if len(self.__heap) > 0:
                    next_time = min(next_time, self.__heap[0].time)

                await sleep_until(next_time)

        except asyncio.CancelledError:
            # Let this through.
            raise

        except Exception:
            # FIXME: Do this in Apsis.
            log.critical("scheduled loop failed", exc_info=True)
            raise SystemExit(1)


    def schedule(self, time: Time, run: Run):
        """
        Schedule `run` to start at `time`.

        If `time` is not in the future, starts the run now.
        """
        wait = time - now()
        if wait <= 0:
            # Job is current; start it now.
            log.info(f"run immediately: {time} {run.run_id}")
            asyncio.ensure_future(self.__start_run(run))

        else:
            # Put it onto the schedule heap.
            log.debug(f"schedule: {time} {run.run_id}")
            entry = self.Entry(time, run)
            heapq.heappush(self.__heap, entry)
            self.__scheduled[run] = entry


    def unschedule(self, run: Run) -> bool:
        """
        Unschedules `run`.

        :return:
          Whether the run was unscheduled: true iff it was scheduled, hasn't
          started yet, and hasn't already been unscheduled.
        """
        log.info(f"unschedule: {run}")
        try:
            # Remove it from the scheduled dict.
            entry = self.__scheduled.pop(run)
        except KeyError:
            # Wasn't scheduled.
            return False
        else:
            # Mark it as unscheduled, so the start loop will ignore it.  Note
            # that we don't remove it from the heap; there's no constant-time
            # way to do this.
            assert entry.scheduled
            entry.scheduled = False
            return True
 


