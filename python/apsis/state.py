from   contextlib import contextmanager
from   pathlib import Path

#-------------------------------------------------------------------------------

class State:

    def __init__(self):
        self.__jobs = []
        self.__executing = {}
        self.__results = []


    def executing(self, run):
        self.__executing[run.id] = run


    def executing_to_result(self, result):
        run = self.__executing.pop(result.run.id)
        assert run is result.run
        self.__results.append(run)


    def add_job(self, job):
        self.__jobs.append(job)


    def get_jobs(self):
        return iter(self.__jobs)


    def get_results(self):
        return iter(self.__results)



state = State()

