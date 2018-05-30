import asyncio
from   contextlib import contextmanager
import heapq
import itertools
import logging
from   ora import now, Time

from   .lib import Interval
from   .lib.itr import take_last
from   .types import Run, Instance, ProgramFailure, ProgramError
from   .rundb_sa import SQLAlchemyRunDB

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Clean this up and move to a new module.

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
        log.info("add run: {}".format(run))
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


    def query(self, *, job_id=None, since=None, until=None):
        """
        @return
          When, and iterable of runs.
        """
        start   = None if since is None else int(since)
        stop    = len(self.__runs) if until is None else int(until)
        runs    = iter(self.__runs[start : stop])
        if job_id is not None:
            runs = ( r for r in runs if r.inst.job_id == job_id )
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
            log.info("schedule: {} for {}".format(run, run.inst.time))
            heapq.heappush(self.__runs, (run.inst.time, run))
        self.__stop = stop


    def push_now(self, runs):
        for run in runs:
            log.info("schedule: {} now".format(run))
            heapq.heappush(self.__runs, (self.__start, run))


    def cancel(self, *runs):
        # FIXME: Not particularly efficient.
        self.__runs = [ r for r in self.__runs if r[1] not in runs ]
        heapq.heapify(self.__runs)


    def reschedule_now(self, *runs):
        # FIXME: This is not particularly efficient, and doesn't check that the
        # runs are currently scheduled.
        for i, (_, run) in enumerate(self.__runs):
            if run in runs:
                self.__runs[i] = self.__start, run
        heapq.heapify(self.__runs)


    def pop(self, interval):
        start, stop = interval
        assert start == self.__start
        assert stop <= self.__stop

        runs = []
        while len(self.__runs) > 0 and self.__runs[0][0] < stop:
            time, run = heapq.heappop(self.__runs)
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
                args = schedule.bind_args(job.params, sched_time)
                inst = Instance(job.job_id, args, sched_time)
                run = Run(next(STATE.runs.run_ids), inst)
                run.times["schedule"] = str(sched_time)
                yield run


async def schedule_runs(docket, time: Time, jobs):
    """
    Schedules instances of `jobs` until `time`.
    """
    time = Time(time)
    if time <= docket.interval.stop:
        # Nothing to do.
        return

    interval = Interval(docket.interval.stop, time)
    runs = list(get_schedule_runs(interval, jobs=jobs))

    # FIXME: Is this the right place to do this?
    async def add_run(run):
        run.state = Run.SCHEDULED
        await STATE.runs.add(run)

    # Create the run.
    await asyncio.gather(*( add_run(r) for r in runs ))
    docket.push(runs, interval)


async def docket_handler(docket):
    """
    Runs jobs in `docket` currently handled, and rescheduled the handler.
    """
    docket.handle = None

    log.info("docket_handler running")

    time = now()
    # Schdule additional runs.
    await schedule_runs(docket, time + 1 * 86400, STATE.jobs)
    # Run currently-scheduled jobs.
    run_current(docket, time)
    # Reschedule this handler.
    schedule_docket_handler(docket, time)


MAX_DELAY = 60

def schedule_docket_handler(docket, time):
    # When is the next run?
    next_time = time + MAX_DELAY
    if len(docket) > 0:
        next_time = min(docket.next_sched_time, next_time)

    if docket.handle is not None:
        if docket.handle[0] == next_time:
            # The handler is already scheduled.
            log.debug("handler already scheduled")
            return
        else:
            log.debug("cancelling handler for {}".format(docket.handle[0]))
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

async def cancel(run):
    assert run.state == run.SCHEDULED
    STATE.docket.cancel(run)
    run.state = run.ERROR
    await STATE.runs.update(run)


async def start(run):
    assert run.state == run.SCHEDULED
    STATE.docket.reschedule_now(run)
    schedule_docket_handler(STATE.docket, now())


async def rerun(run):
    # Create the new run.
    new_run = Run(next(STATE.runs.run_ids), run.inst)
    new_run.state = Run.SCHEDULED
    when = await STATE.runs.add(new_run)

    # Schedule it for immediate execution.
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
        # FIXME: Is this the right way to get the job?
        job = STATE.get_job(run.inst.job_id)
        asyncio.ensure_future(execute(run, job))


#-------------------------------------------------------------------------------

async def execute(run, job):
    # Start it.
    program = job.program
    execute_time = now()
    run.times["execute"] = str(execute_time)
    log.info(f"executing: {run.run_id}")
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
    log.info(f"done: {run.run_id} {run.state}")
    done_time = now()
    run.times["done"] = str(done_time)
    await STATE.runs.update(run)


#-------------------------------------------------------------------------------

class State:

    def __init__(self):
        self.jobs = []
        self.runs = SQLAlchemyRunDB.create("./apsis.sqlite")  # FIXME
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

