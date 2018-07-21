import itertools
from   ora import Time

from   .runs import Instance, Run

#-------------------------------------------------------------------------------

class Scheduler:

    def __init__(self, jobs, start: Time):
        self.__jobs = jobs
        self.__stop = start


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



