import asyncio
import logging
from   ora import Time, now

from   .lib import Interval
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
            self.get_program(run).reconnect(run)


    # --------------------------------------------------------------------------

    def get_program(self, run):
        job = self.jobs.get_job(run.inst.job_id)
        program = bind_program(job.program, run)
        return program


    async def __start(self, run):
        await self.get_program(run).start(run)


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


    # --- API ------------------------------------------------------------------

    async def schedule(self, time, run):
        """
        Adds and schedules a new run.
        """
        self.runs.add(run)
        run.to_scheduled(times={"schedule": time})
        self.scheduled.schedule(time, run)


    async def cancel(self, run):
        self.scheduled.unschedule(run)
        run.to_error("cancelled")


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



