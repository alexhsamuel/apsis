from   aslib.itr import take_last
import asyncio
from   contextlib import contextmanager
from   cron import *
import itertools
import logging
from   pathlib import Path

log = logging.getLogger("state")

#-------------------------------------------------------------------------------

class Runs:
    # FIXME: Very inefficient.

    def __init__(self):
        self.__runs     = []
        self.__queues   = set()
        self.run_ids    = ( "run" + str(i) for i in itertools.count() )


    def __add(self, run):
        self.__runs.append(run)
        when = str(len(self.__runs))
        self.__send(when, run)
        return when


    async def add(self, run):
        assert not any( r.run_id == run.run_id for r in self.__runs )
        return self.__add(run)


    # FIXME: Sloppy API.  Are we mutating the run, or replacing it?
    async def update(self, run):
        assert any( r.run_id == run.run_id for r in self.__runs )
        return self.__add(run)


    async def get(self, run_id):
        when = str(len(self.__runs))
        run = take_last( r for r in self.__runs if r.run_id == run_id )
        return when, run


    async def query(self, *, since=None, until=None):
        """
        @return
          When, and iterable of runs.
        """
        start   = None if since is None else int(since)
        stop    = len(self.__runs) if until is None else int(until)
        runs    = iter(self.__runs[start : stop])
        return str(stop), runs


    @contextmanager
    def query_live(self, *, since=None):
        queue = asyncio.Queue()
        self.__queues.add(queue)

        when    = str(len(self.__runs))
        start   = None if since is None else int(since)
        runs    = self.__runs[start :]
        queue.put_nowait((when, runs))

        try:
            yield queue
        finally:
            self.__queues.remove(queue)


    def __send(self, when, run):
        for queue in self.__queues:
            queue.put_nowait((when, [run]))  # FIXME: Nowait?



#-------------------------------------------------------------------------------

class State:

    def __init__(self):
        self.__jobs = []
        self.runs = Runs()


    def add_job(self, job):
        self.__jobs.append(job)


    def get_job(self, job_id):
        # FIXME
        job, = [ j for j in self.__jobs if j.job_id == job_id ]
        return job


    def get_jobs(self):
        return iter(self.__jobs)



STATE = State()

