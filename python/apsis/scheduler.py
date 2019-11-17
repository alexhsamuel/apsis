import asyncio
import itertools
import logging
from   ora import Time, now

from   .runs import Instance, Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Scheduler:

    HORIZON = 86400

    def __init__(self, cfg, jobs, schedule, stop):
        """
        :param jobs:
          The jobs repo.
        :param schedule:
          Function of `time, run` that schedules a run.
        """
        self.__cfg = cfg
        self.__jobs = jobs
        self.__stop = stop
        self.__schedule = schedule

        since = self.__cfg.get("schedule_since")
        if since is not None:
            since = Time(since)
            if since > self.__stop:
                self.__stop = since


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
                    lambda t: t[0] < stop, schedule(self.__stop))

                for sched_time, args in times:
                    args = {**args, "schedule_time": sched_time}
                    args = { 
                        a: str(v) 
                        for a, v in args.items() 
                        if a in job.params
                    }
                    # FIXME: Store additional args for later expansion.
                    inst = Instance(job.job_id, args)

                    if schedule.enabled:
                        # Runs instantiated by the scheduler are only expected;
                        # the job schedule may change before the run is started.
                        yield sched_time, Run(inst, expected=True)

        self.__stop = stop


    async def schedule(self, stop):
        """
        Schedules runs until `stop`.
        """
        assert stop >= self.__stop

        log.debug(f"scheduling runs until {stop}")
        for time, run in self.get_runs(stop):
            await self.__schedule(time, run)

        self.__stop = stop


    async def loop(self):
        """
        Infinite loop that periodically schedules runs.
        """
        while True:
            try:
                # Make sure we're not too old.
                time = now()
                log.debug(f"scheduler loop: {time}")
                try:
                    max_age = self.__cfg.get("schedule_max_age")
                except KeyError:
                    pass
                else:
                    if max_age is not None and time - self.__stop > float(max_age):
                        raise RuntimeError(
                            f"last scheduled more than "
                            f"schedule_max_age ({max_age} s) ago"
                        )

                await self.schedule(time + self.HORIZON)

                await asyncio.sleep(60)

            except asyncio.CancelledError:
                log.info("scheduler loop cancelled")
                break

            except Exception:
                log.critical("scheduler loop failed", exc_info=True)
                raise SystemExit(1)



