import asyncio
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
        self.__queues = set()


    def add(self, result):
        self.__results.append(result)
        for queue in self.__queues:
            queue.put_nowait([result])  # FIXME: Nowait?
        return str(len(self.__results))


    async def query(self, *, since=None, until=None):
        """
        @return
          When, and iterable of results.
        """
        start   = None if since is None else int(since)
        stop    = len(self.__results) if until is None else int(until)
        results = iter(self.__results[start : stop])
        return str(stop), results


    @contextmanager
    def query_live(self, *, since=None):
        queue = asyncio.Queue()
        self.__queues.add(queue)

        start   = None if since is None else int(since)
        results = self.__results[start :]
        queue.put_nowait(results)

        try:
            yield queue
        finally:
            self.__queues.remove(queue)



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

