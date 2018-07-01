import asyncio
import logging
from   pathlib import Path
from   ora import Time, now
import sqlalchemy as sa

from   .lib import Interval
from   .types import Job
from   .runs import Run, Runs
from   .rundb_sa import SQLAlchemyRunDB
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

class DB:
    """
    A SQLite3 file containing persistent state.
    """

    def __init__(self, path, create=False):
        path    = Path(path).absolute()
        if create and path.exists():
            raise FileExistsError(path)
        if not create and not path.exists():
            raise FileNotFoundError(path)

        url     = self.__get_url(path)
        engine  = sa.create_engine(url)
        run_db  = SQLAlchemyRunDB(engine, create)

        self.run_db = run_db


    @classmethod
    def __get_url(Class, path):
        # For now, sqlite only.
        return f"sqlite:///{path}"



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
        # FIXME: Restore scheduled runs from DB.


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
            self.runs.add(run)
            run.to_scheduled()
            self.scheduled.schedule(time, run)


    async def scheduler_loop(self, interval=86400):
        while True:
            await self.__schedule_runs(now() + interval)
            await asyncio.sleep(60)


    async def __start(self, run):
        job = self.get_job(run.inst.job_id)
        program = bind_program(job.program, run)
        await program.start(run)


    # --- API ------------------------------------------------------------------

    async def cancel(self, run):
        self.scheduled.unschedule(run)
        run.to_error("cancelled")


    async def start(self, run):
        # FIXME: Race conditions?
        self.scheduled.unschedule(run)
        await self.__start(run)


    async def rerun(self, run):
        # FIXME: Not updated, so broken.

        # Create the new run.
        new_run = Run(run.inst)
        self.runs.add(new_run)
        await self.__start(new_run)
        return new_run



