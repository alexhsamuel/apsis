from   aslib.itr import take_last
import asyncio
from   contextlib import contextmanager
from   cron import *
import heapq
import itertools
import logging
from   pathlib import Path

from   .execute import Run, ProgramError, ProgramFailure
from   .job import Instance
from   .lib import *

log = logging.getLogger("state")

#-------------------------------------------------------------------------------

class Runs:
    # FIXME: Very inefficient.

    def __init__(self):
        self.__runs     = []
        self.__queues   = set()
        self.run_ids    = ( "run" + str(i) for i in itertools.count() )


    def __add(self, run):
        self.__runs.append(run)
        when = str(len(self.__runs))
        self.__send(when, run)
        return when


    async def add(self, run):
        assert not any( r.run_id == run.run_id for r in self.__runs )
        return self.__add(run)


    # FIXME: Sloppy API.  Are we mutating the run, or replacing it?
    async def update(self, run):
        assert any( r.run_id == run.run_id for r in self.__runs )
        return self.__add(run)


    async def get(self, run_id):
        when = str(len(self.__runs))
        run = take_last( r for r in self.__runs if r.run_id == run_id )
        return when, run


    def query(self, *, since=None, until=None):
        """
        @return
          When, and iterable of runs.
        """
        start   = None if since is None else int(since)
        stop    = len(self.__runs) if until is None else int(until)
        runs    = iter(self.__runs[start : stop])
        return str(stop), runs


    @contextmanager
    def query_live(self, *, since=None):
        queue = asyncio.Queue()
        self.__queues.add(queue)

        when    = str(len(self.__runs))
        start   = None if since is None else int(since)
        runs    = self.__runs[start :]
        queue.put_nowait((when, runs))

        try:
            yield queue
        finally:
            self.__queues.remove(queue)


    def __send(self, when, run):
        for queue in self.__queues:
            queue.put_nowait((when, [run]))  # FIXME: Nowait?



#-------------------------------------------------------------------------------

class Docket:
    """
    Scheduled runs waiting to execute.
    """

    def __init__(self):
        time = now()  # FIXME: ??
        self.__start    = time
        self.__stop     = time
        self.__runs     = []
        self.handle     = None


    def __len__(self):
        return len(self.__runs)


    @property
    def interval(self):
        return Interval(self.__start, self.__stop)


    @property
    def next_sched_time(self):
        """
        The time of the next scheduled run.
        """
        if len(self.__runs) > 0:
            return self.__runs[0][0]
        else:
            raise RuntimeError("no scheduled runs")


    def push(self, runs, interval):
        start, stop = interval
        assert start == self.__stop
        for run in runs:
            assert run.inst.time in interval
            log.info("pushing: ({}) {}".format(run.inst.time, run.run_id))
            heapq.heappush(self.__runs, (run.inst.time, run))
        self.__stop = stop


    def push_now(self, runs):
        for run in runs:
            log.info("pushing: {}".format(run.run_id))
            heapq.heappush(self.__runs, (self.__start, run))


    def pop(self, interval):
        start, stop = interval
        assert start == self.__start
        assert stop <= self.__stop

        runs = []
        while len(self.__runs) > 0 and self.__runs[0][0] < stop:
            time, run = heapq.heappop(self.__runs)
            log.info("popping: ({}) {}".format(time, run.run_id))
            runs.append(run)
        self.__start = stop
        return runs



def get_schedule_runs(times: Interval, jobs):
    """
    Generates runs scheduled in interval `times`.
    """
    start, stop = times
    for job in jobs:
        for schedule in job.schedules:
            times = itertools.takewhile(lambda t: t < stop, schedule(start))
            for sched_time in times:
                inst_id = job.job_id + "-" + str(sched_time)
                args = schedule.bind_args(job.params, sched_time)
                inst = Instance(inst_id, job, args, sched_time)
                run = Run(next(STATE.runs.run_ids), inst)
                run.times["schedule"] = str(sched_time)
                yield run


async def schedule_runs(docket, time: Time, jobs):
    """
    Schedules instances of `jobs` until `time`.
    """
    log.info("schedule_runs")

    time = Time(time)
    if time <= docket.interval.stop:
        # Nothing to do.
        return

    interval = Interval(docket.interval.stop, time)
    runs = list(get_schedule_runs(interval, jobs=jobs))

    # FIXME: Is this the right place to do this?
    async def add_run(run):
        run.state = Run.SCHEDULED
        log.info("add_run: {}".format(run))
        await STATE.runs.add(run)

    # Create the run.
    await asyncio.gather(*( add_run(r) for r in runs ))
    docket.push(runs, interval)

    log.info("schedule_runs done")


async def docket_handler(docket):
    """
    Runs jobs in `docket` currently handled, and rescheduled the handler.
    """
    docket.handle = None

    log.info("docket_handler")

    time = now()
    # Schdule additional runs.
    await schedule_runs(docket, time + 1 * 86400, STATE.jobs)
    # Run currently-scheduled jobs.
    run_current(docket, time)
    # Reschedule this handler.
    schedule_docket_handler(docket, time)

    log.info("docket_handler done")


MAX_DELAY = 60

def schedule_docket_handler(docket, time):
    # When is the next run?
    next_time = time + MAX_DELAY
    if len(docket) > 0:
        next_time = min(docket.next_sched_time, next_time)

    if docket.handle is not None:
        if docket.handle[0] == next_time:
            # The handler is already scheduled.
            log.info("handler already scheduled")
            return
        else:
            log.info("cancelling handler for {}".format(docket.handle[0]))
            docket.handle[1].cancel()
            docket.handle = None

    # Schedule the handler.
    delay = next_time - time
    log.info(
        "docket_handler scheduled for {}, delay {}".format(next_time, delay))
    loop = asyncio.get_event_loop()
    # FIXME: Is this really how to schedule a coroutine in the future?
    handle = loop.call_later(
        delay, asyncio.ensure_future, docket_handler(docket))

    # Store the callback handle and the time at which it is scheduled.
    docket.handle = next_time, handle


def start_docket(docket):
    asyncio.ensure_future(docket_handler(docket))


#-------------------------------------------------------------------------------

async def rerun(run):
    new_run = Run(next(STATE.runs.run_ids), run.inst, run.number + 1)
    new_run.state = Run.SCHEDULED
    when = await STATE.runs.add(new_run)
    STATE.docket.push_now([new_run])
    schedule_docket_handler(STATE.docket, now())
    return when, new_run


def extract_current_runs(docket, time: Time):
    """
    Removes and returns current runs as of `time`.
    """
    time = Time(time)
    assert docket.interval.start <= time <= docket.interval.stop
    interval = Interval(docket.interval.start, time)
    return docket.pop(interval)


def run_current(docket, time):
    """
    Executes runs in `docket` that are current at `time`.
    """
    # FIXME: Check if the docket is behind.
    runs = extract_current_runs(docket, time)
    for run in runs:
        asyncio.ensure_future(execute(run))


#-------------------------------------------------------------------------------

async def execute(run):
    # FIXME: STARTING state?

    # Start it.
    program = run.inst.job.program
    execute_time = now()
    run.times["execute"] = str(execute_time)
    try:
        proc = await program.start(run)
    except ProgramError as exc:
        run.meta["error"] = str(exc)
        run.state = Run.ERROR
    else:
        # Started successfully.
        run.state = Run.RUNNING
        run.times["running"] = str(now())
        await STATE.runs.update(run)
        # Wait for it to complete.
        try:
            await program.wait(run, proc)
        except ProgramFailure as exc:
            run.meta["failure"] = str(exc)
            run.state = Run.FAILURE
        else:
            run.state = Run.SUCCESS
    done_time = now()
    run.times["done"] = str(done_time)
    run.times["elapsed"] = done_time - execute_time
    await STATE.runs.update(run)



#-------------------------------------------------------------------------------

class State:

    def __init__(self):
        self.jobs = []
        self.runs = Runs()
        self.docket = Docket()


    def add_job(self, job):
        self.jobs.append(job)


    def get_job(self, job_id):
        # FIXME
        job, = [ j for j in self.jobs if j.job_id == job_id ]
        return job


    def get_jobs(self):
        return iter(self.jobs)



STATE = State()

