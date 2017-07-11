from   contextlib import contextmanager
from   cron import *
import itertools
import logging
from   pathlib import Path

log = logging.getLogger("state")

#-------------------------------------------------------------------------------

class Results:

    def __init__(self):
        self.__results = []


    def add(self, result):
        self.__results.append(result)
        return str(len(self.__results))


    async def query(self, *, until=None, since=None, job_ids=None):
        """
        @return
          When, and iterable of results.
        """
        start = None if since is None else int(since)
        stop  = None if until is None else int()
        results = iter(self.__results[start : stop])

        if job_ids is not None:
            results = ( 
                r for r in results 
                if any( r.run.inst.job.job_id == i for i in job_ids )
            )
        return str(len(self.__results)), results



class State:

    def __init__(self):
        self.run_ids = ( str(i) for i in itertools.count() )
        self.__jobs = []
        self.__executing = {}
        self.results = Results()


    def executing(self, run):
        self.__executing[run.run_id] = run


    def executing_to_result(self, result):
        run = self.__executing.pop(result.run.run_id)
        assert run is result.run
        self.results.add(result)


    def add_job(self, job):
        self.__jobs.append(job)


    def get_job(self, job_id):
        # FIXME
        job, = [ j for j in self.__jobs if j.job_id == job_id ]
        return job


    def get_jobs(self):
        return iter(self.__jobs)



state = State()

