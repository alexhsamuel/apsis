import asyncio
import logging
from   ora import Time, now

from   .lib import Interval
from   .program import ProgramError, ProgramFailure
from   .runs import Run, Runs
from   .scheduled import ScheduledRuns
from   .scheduler import Scheduler

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def extract_current_runs(docket, time: Time):
    """
    Removes and returns current runs as of `time`.
    """
    time = Time(time)
    assert docket.interval.start <= time <= docket.interval.stop
    interval = Interval(docket.interval.start, time)
    return docket.pop(interval)


def bind_program(program, run):
    return program.bind({
        "run_id": run.run_id,
        "job_id": run.inst.job_id,
        **run.inst.args,
    })


#-------------------------------------------------------------------------------

class Apsis:
    """
    The gestalt scheduling application.
    """

    def __init__(self, jobs, db):
        self.__db = db
        self.jobs = jobs

        # Continue scheduling where we left off.
        scheduler_stop = db.scheduler_db.get_stop()
        self.scheduler = Scheduler(self.jobs, scheduler_stop)

        self.runs = Runs(db.run_db)

        self.scheduled = ScheduledRuns(self.__start)

        # Restore scheduled runs from DB.
        _, scheduled_runs = self.runs.query(state=Run.STATE.scheduled)
        for run in scheduled_runs:
            self.scheduled.schedule(run.times["schedule"], run)

        # Reconnect to running runs.
        _, running_runs = self.runs.query(state=Run.STATE.running)
        for run in running_runs:
            future = self.__get_program(run).reconnect(run)
            self.__wait(run, future)


    def __get_program(self, run):
        job = self.jobs.get_job(run.inst.job_id)
        program = bind_program(job.program, run)
        return program


    async def __start(self, run):
        try:
            running, coro = await self.__get_program(run).start(run)
        except ProgramError as exc:
            self._transition(run, run.STATE.error, **exc.__dict__)
        else:
            self._transition(run, run.STATE.running, **running.__dict__)

        future = asyncio.ensure_future(coro)
        self.__wait(run, future)


    def __wait(self, run, future):
        def done(future):
            try:
                success = future.result()
            except ProgramFailure as exc:
                self._transition(run, run.STATE.failure, **exc.__dict__)
            else:
                self._transition(run, run.STATE.success, **success.__dict__)

        future.add_done_callback(done)


    async def __schedule_runs(self, timestamp: Time):
        """
        Schedules instances of jobs until `time`.
        """
        log.info("schedling runs")
        runs = self.scheduler.get_runs(timestamp)

        for time, run in runs:
            await self.schedule(time, run)


    async def scheduler_loop(self, interval=86400):
        while True:
            stop = now() + interval
            await self.__schedule_runs(stop)
            self.__db.scheduler_db.set_stop(stop)
            await asyncio.sleep(60)


    # --- Internal API ---------------------------------------------------------

    def _transition(self, run, state, **kw_args):
        timestamp = now()
        # Transition the run object.
        run._transition(timestamp, state, **kw_args)
        # Store the new state.
        self.runs.update(run, timestamp)


    def _to_running(self, run, run_state, *, meta={}, times={}):
        run._transition(
            Run.STATE.running, 
            meta=meta, times=times, run_state=run_state)


    def _to_error(self, run, message, *, meta={}, times={}, output=None):
        run._transition(
            Run.STATE.error, 
            message=message, meta=meta, times=times, output=output)


    def _to_success(self, run, *, meta={}, times={}, output=None):
        run._transition(
            Run.STATE.success, 
            meta=meta, times=times, output=output)

        
    def _to_failure(self, run, message, *, meta={}, times={}, output=None):
        run._transition(
            Run.STATE.failure, 
            message=message, meta=meta, times=times, output=output)


    # --- API ------------------------------------------------------------------

    async def schedule(self, time, run):
        """
        Adds and schedules a new run.
        """
        self.runs.add(run)
        self.scheduled.schedule(time, run)
        self._transition(run, run.STATE.scheduled, times={"schedule": time})


    async def cancel(self, run):
        self.scheduled.unschedule(run)
        self._transition(run, run.STATE.error, message="cancelled")


    async def start(self, run):
        # FIXME: Race conditions?
        self.scheduled.unschedule(run)
        await self.__start(run)


    async def rerun(self, run):
        # Create the new run.
        log.info(f"rerun: {run.run_id}")
        new_run = Run(run.inst, rerun_of=run.run_id)
        self.runs.add(new_run)
        run.set_rerun(new_run.run_id)
        await self.__start(new_run)
        return new_run



