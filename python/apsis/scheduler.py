import asyncio
import itertools
import logging
from   ora import Time, now

from   .runs import Instance, Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Scheduler:

    HORIZON = 86400

    def __init__(self, jobs, db, schedule):
        """
        :param jobs:
          The jobs repo.
        :param db:
          The scheduler DB, for persisting state.
        :param schedule:
          Function of `time, run` that schedules a run.
        """
        self.__jobs = jobs
        self.__db = db
        self.__stop = db.get_stop()
        self.__schedule = schedule


    def get_runs(self, stop: Time):
        """
        Generates runs scheduled in interval `times`.

        :return:
          Iterable of (time, run) pairs.
        """
        if stop <= self.__stop:
            # Nothing to do.
            return

        for job in self.__jobs.get_jobs():
            for schedule in job.schedules:
                times = itertools.takewhile(
                    lambda t: t < stop, schedule(self.__stop))

                for sched_time in times:
                    args = schedule.bind_args(job.params, sched_time)
                    inst = Instance(job.job_id, args)
                    if schedule.enabled:
                        yield sched_time, Run(inst)

        self.__stop = stop


    async def schedule(self, stop):
        """
        Schedules runs until `stop`.
        """
        assert stop >= self.__stop

        log.info(f"schedling runs until {stop}")
        for time, run in self.get_runs(stop):
            await self.__schedule(time, run)

        self.__stop = stop
        self.__db.set_stop(stop)


    async def loop(self):
        """
        Infinite loop that periodically schedules runs.
        """
        while True:
            await self.schedule(now() + self.HORIZON)
            await asyncio.sleep(60)



