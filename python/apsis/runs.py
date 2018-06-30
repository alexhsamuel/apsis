import asyncio
from   contextlib import contextmanager
import enum
import itertools
import logging
from   ora import now

from   .lib.py import format_ctor

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class TransitionError(RuntimeError):

    def __init__(self, from_state, to_state):
        super().__init__(f"cannot transition from {from_state} to {to_state}")



#-------------------------------------------------------------------------------

class Runs:
    """
    Stores run state.

    Responsible for:
    1. Creating new runs.
    1. Managing run IDs.
    1. Storing runs, in all states.
    1. Satisfying run queries.
    1. Serving live queries of runs.
    """

    # FIXME: For now, we cache all runs in memory.  At some point, we'll need
    # to start retiring older runs.

    def __init__(self, db):
        self.__db = db

        # Populate cache from database.
        self.__runs = {}
        for run in self.__db.query():
            run._Run__runs = self
            self.__runs[run.run_id] = run

        # FIXME: Do this better.
        run_ids = ( int(r.run_id[1 :]) for r in self.__runs.values() )
        max_run_id = max(run_ids, default=0)
        self.__run_ids = ( "r" + str(i) for i in itertools.count(max_run_id) )

        # For live notification.
        self.__queues = set()


    def __send(self, when, run):
        """
        Sends live notification of changes to `run`.
        """
        for queue in self.__queues:
            queue.put_nowait((when, [run]))


    def add(self, run):
        assert run.state == Run.STATE.new

        timestamp = now()
        run_id = next(self.__run_ids)
        assert run.run_id not in self.__runs

        run._Run__runs  = self
        run.run_id      = run_id
        run.timestamp   = timestamp

        log.info(f"new run: {run}")

        self.__runs[run.run_id] = run
        self.__db.insert(run)
        self.__send(timestamp, run)


    def update(self, run, timestamp):
        # Make sure we know about this run.
        assert self.__runs[run.run_id] is run
        # Persist the changes.
        self.__db.update(run)
        self.__send(timestamp, run)


    def get(self, run_id):
        run = self.__runs[run_id]
        return now(), run


    def query(self, *, job_id=None, since=None, until=None):
        runs = self.__runs.values()
        if job_id is not None:
            runs = ( r for r in runs if r.inst.job_id == job_id )
        if since is not None:
            runs = ( r for r in runs if r.timestamp >= since )
        if until is not None:
            runs = ( r for r in runs if r.timestamp < until )

        return now(), runs


    @contextmanager
    def query_live(self, *, since=None, **kw_args):
        queue = asyncio.Queue()
        self.__queues.add(queue)

        when, runs = self.query(since=since, **kw_args)
        queue.put_nowait((when, runs))

        try:
            yield queue
        finally:
            self.__queues.remove(queue)



#-------------------------------------------------------------------------------

class Run:

    STATE = enum.Enum(
        "Run.STATE", 
        (
            "new", 
            "scheduled", 
            "running",
            "success",
            "failure",
            "error",
        )
    )

    # FIXME: Make the attributes read-only.

    def __init__(self, inst):
        self.inst       = inst

        self.__runs     = None
        self.run_id     = None
        self.timestamp  = None

        self.state      = Run.STATE.new
        self.times      = {}
        self.meta       = {}
        self.message    = None
        self.output     = None
        self.run_state  = None


    def __hash__(self):
        return hash(self.run_id)


    def __eq__(self, other):
        assert other.run_id == self.run_id


    def __repr__(self):
        return format_ctor(self, self.run_id, self.inst, state=self.state)


    def __str__(self):
        return f"{self.run_id} {self.state.name} {self.inst}"


    def __transition(self, state, *, meta={}, times={}, 
                     output=None, message=None, run_state=None):
        timestamp = now()

        # Update attributes.
        self.timestamp = timestamp
        self.meta.update(meta)
        self.times[state.name] = self.timestamp
        self.times.update(times)
        self.output = output
        self.message = str(message)
        self.run_state = run_state

        # Transition to the new state.
        self.state = state

        # Apply the changes.
        self.__runs.update(self, timestamp)


    def to_scheduled(self, *, meta={}, times={}):
        if self.state not in {Run.STATE.new}:
            raise TransitionError(self.state, Run.STATE.scheduled)
        self.__transition(
            Run.STATE.scheduled, 
            meta=meta, times=times)


    def to_running(self, run_state, *, meta={}, times={}):
        if self.state not in {Run.STATE.new, Run.STATE.scheduled}:
            raise TransitionError(self.state, Run.STATE.running)
        self.__transition(
            Run.STATE.running, 
            meta=meta, times=times, run_state=run_state)


    def to_error(self, message, *, meta={}, times={}, output={}):
        if self.state not in {Run.STATE.new, Run.STATE.scheduled}:
            raise TransitionError(self.state, Run.STATE.error)
        self.__transition(
            Run.STATE.error, 
            message=message, meta=meta, times=times, output=output)


    def to_success(self, *, meta={}, times={}, output={}):
        if self.state != Run.STATE.running:
            raise TransitionError(self.state, Run.STATE.success)
        self.__transition(
            Run.STATE.success, 
            meta=meta, times=times, output=output)

        
    def to_failure(self, message, *, meta={}, times={}, output={}):
        if self.state != Run.STATE.running:
            raise TransitionError(self.state, Run.STATE.failure)
        self.__transition(
            Run.STATE.failure, 
            message=message, meta=meta, times=times, output=output)



#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------

class Instance:
    """
    A job with bound parameters.  Not user-visible.
    """

    def __init__(self, job_id, args):
        self.job_id     = job_id
        self.args       = { str(k): str(v) for k, v in args.items() }


    def __repr__(self):
        return format_ctor(self, self.job_id, self.args)


    def __str__(self):
        return "{}({})".format(
            self.job_id, 
            " ".join( "{}={}".format(k, v) for k, v in self.args.items() )
        )


    def __hash__(self):
        return hash(self.job_id) ^ hash(tuple(sorted(self.args.items())))


    def __eq__(self, other):
        return (
            self.job_id == other.job_id
            and self.args == other.args
        ) if isinstance(other, Instance) else NotImplemented


    def __lt__(self, other):
        return (
            self.job_id < other.job_id
            or (
                self.job_id == other.job_id
                and sorted(self.args.items()) < sorted(other.args.items())
            )
        ) if isinstance(other, Instance) else NotImplemented



