from   contextlib import contextmanager
import itertools
from   pathlib import Path

#-------------------------------------------------------------------------------

class State:

    def __init__(self):
        self.run_ids = ( str(i) for i in itertools.count() )
        self.__jobs = []
        self.__executing = {}
        self.__results = []


    def executing(self, run):
        self.__executing[run.run_id] = run


    def executing_to_result(self, result):
        run = self.__executing.pop(result.run.run_id)
        assert run is result.run
        self.__results.append(result)


    def add_job(self, job):
        self.__jobs.append(job)


    def get_job(self, job_id):
        # FIXME
        job, = [ j for j in self.__jobs if j.job_id == job_id ]
        return job


    def get_jobs(self):
        return iter(self.__jobs)


    def get_results(self):
        return iter(self.__results)


    def get_result(self, run_id):
        # FIXME
        result, = [ r for r in self.__results if r.run.run_id == run_id ]
        return result



state = State()

