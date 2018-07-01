import asyncio
import logging
from   ora import Time, now

from   .jobs import Job
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

    def __init__(self, db):
        # FIXME: Back-populate runs?
        start_time = now()

        self.jobs = []
        self.scheduler = Scheduler(self.jobs, start_time)
        self.runs = Runs(db.run_db)
        self.scheduled = ScheduledRuns(self.__start)

        # Restore scheduled runs from DB.
        _, scheduled_runs = self.runs.query(state=Run.STATE.scheduled)
        for run in scheduled_runs:
            self.scheduled.schedule(run.times["schedule"], run)


    # --------------------------------------------------------------------------

    # FIXME: Encapsulate job stuff.

    def add_job(self, job):
        self.jobs.append(job)


    def get_job(self, job_id) -> Job:
        """
        :raise LookupError:
          Can't find `job_id`.
        """
        jobs = [ j for j in self.jobs if j.job_id == job_id ]
        if len(jobs) == 0:
            raise LookupError(job_id)
        else:
            assert len(jobs) == 1
            return jobs[0]


    def get_jobs(self):
        return iter(self.jobs)


    # --------------------------------------------------------------------------

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
            await self.__schedule_runs(now() + interval)
            await asyncio.sleep(60)


    async def __start(self, run):
        job = self.get_job(run.inst.job_id)
        program = bind_program(job.program, run)
        await program.start(run)


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



