import asyncio
from   contextlib import contextmanager
import enum
import itertools
import logging
from   ora import now, Time

from   .lib.py import format_ctor

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class TransitionError(RuntimeError):

    def __init__(self, from_state, to_state):
        super().__init__(f"cannot transition from {from_state} to {to_state}")



class RunError(RuntimeError):

    pass



class MissingArgumentError(RunError):

    def __init__(self, run, *args):
        super().__init__(
            f"missing args ({', '.join(args)}) for job {run.inst.job_id}")



class ExtraArgumentError(RunError):

    def __init__(self, run, *args):
        super().__init__(
            f"extra args ({', '.join(args)}) for job {run.inst.job_id}")



#-------------------------------------------------------------------------------

class Instance:
    """
    A job with bound parameters.  Not user-visible.
    """

    def __init__(self, job_id, args):
        self.job_id = job_id
        self.args   = dict(sorted( (str(k), str(v)) for k, v in args.items() ))


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



#-------------------------------------------------------------------------------

class Run:
    """
    :ivar rerun:
      The run ID of the original run of which this is a rerun.  If this is not
      a rerun, equal to the run ID.  (This attribute partitions groups by 
      initial run ID.)
    """

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

    # Allowed transitions to each state.
    TRANSITIONS = {
        STATE.new       : set(),
        STATE.scheduled : {STATE.new},
        STATE.running   : {STATE.new, STATE.scheduled},
        STATE.error     : {STATE.new, STATE.scheduled, STATE.running},
        STATE.success   : {STATE.running},
        STATE.failure   : {STATE.running},
    }

    # FIXME: Make the attributes read-only.

    def __init__(self, inst, *, rerun=None, expected=False):
        """
        :param rerun:
          The run ID of which this is a rerun, or `None` if this is not a rerun.
        :param expected:
          True if this run was scheduled from a job schedule.  A run scheduled
          from a job schedule is subject to change, as the job's schedules may
          change.
        """
        self.inst       = inst

        self.run_id     = None
        self.timestamp  = None

        self.state      = Run.STATE.new
        self.expected   = bool(expected)
        self.program    = None
        # Timestamps for state transitions and other events.
        self.times      = {}
        # Additional run metadata.
        self.meta       = {}
        # User message explaining the state.
        self.message    = None
        # State information specific to the program, for a running run.
        self.run_state  = None

        self.rerun      = rerun


    def __hash__(self):
        return hash(self.run_id)


    def __eq__(self, other):
        assert other.run_id == self.run_id


    def __repr__(self):
        return format_ctor(
            self, self.run_id, self.inst, state=self.state, rerun=self.rerun)


    def __str__(self):
        return f"{self.run_id} {self.state.name} {self.inst}"


    def _transition(self, timestamp, state, *, meta={}, times={}, 
                    message=None, run_state=None):
        # Check that this is a valid transition.
        if self.state not in self.TRANSITIONS[state]:
            raise TransitionError(self.state, state)

        assert all( isinstance(t, Time) and t.valid for t in times.values() )

        log.debug(f"transition {self.run_id}: {self.state.name} → {state.name}")

        # Update attributes.
        self.timestamp = timestamp
        self.message = None if message is None else str(message)
        self.meta.update(meta)
        self.times[state.name] = self.timestamp
        self.times.update(times)
        self.run_state = run_state

        # Compute and add elapsed time.
        start = self.times.get("running")
        end = self.times.get("success", self.times.get("failure"))
        if start is not None and end is not None:
            elapsed = end - start
            log.debug(f"elapsed time: {self.run_id}: {elapsed}")
            self.meta["elapsed"] = elapsed
       
        # Transition to the new state.
        self.state = state



#-------------------------------------------------------------------------------

class Runs:
    """
    Stores run state.

    Responsible for:
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
            self.__runs[run.run_id] = run

        # FIXME: Do this better.
        run_ids = ( int(r.run_id[1 :]) for r in self.__runs.values() )
        start_run_id = max(run_ids, default=0) + 1
        self.__run_ids = ( "r" + str(i) for i in itertools.count(start_run_id) )

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

        run.run_id = run_id
        # If not a rerun, set the rerun ID to the run ID.
        if run.rerun is None:
            run.rerun = run_id

        run.timestamp = timestamp

        log.info(f"new run: {run}")
        self.__runs[run.run_id] = run
        self.update(run, timestamp)


    def update(self, run, timestamp):
        """
        Called when `run` is changed.

        Persists the run if necessary, and sends live update notifications.

        :param insert:
          If true, this is a new run.
        """
        # Make sure we know about this run.
        assert self.__runs[run.run_id] is run

        # Persist the changes.
        if run.expected and run.state in {Run.STATE.new, Run.STATE.scheduled}:
            # Don't persist new or scheduled runs if they are expected; these
            # runs should be recreated from job schedules.
            pass
        else:
            log.debug(f"persisting: {run.run_id}")
            self.__db.upsert(run)

        self.__send(timestamp, run)


    def get(self, run_id):
        run = self.__runs[run_id]
        return now(), run


    def query(self, *, run_ids=None, job_id=None, state=None, rerun=None, 
              since=None, until=None, reruns=True):
        """
        :param reruns:
          If true, include all reruns; otherwise, includes only the latest run
          in each rerun group.
        """
        if run_ids is None:
            runs = self.__runs.values()
        else:
            run_ids = sorted(set(run_ids))
            runs = ( self.__runs.get(i, None) for i in run_ids )
            runs = ( r for r in runs if r is not None )
        if job_id is not None:
            runs = ( r for r in runs if r.inst.job_id == job_id )
        if state is not None:
            runs = ( r for r in runs if r.state == state )
        if rerun is not None:
            runs = ( r for r in runs if r.rerun == rerun )
        if since is not None:
            runs = ( r for r in runs if r.timestamp >= since )
        if until is not None:
            runs = ( r for r in runs if r.timestamp < until )

        if not reruns:
            # FIXME: Make this more efficient.
            groups = {}
            for run in runs:
                groups.setdefault(run.rerun, []).append(run)
            runs = ( 
                max(g, key=lambda r: max(r.times.values(), default=Time.EPOCH))
                for g in groups.values()
            )

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


    async def shut_down(self):
        """
        Terminates any live queries.
        """
        while True:
            try:
                queue = next(iter(self.__queues))
            except StopIteration:
                break

            log.info("shutting down live query queue")
            # Indicate that this queue is shutting down.
            queue.put_nowait(None)
            # FIXME: Join doesn't seem to work.
            # await queue.join()
            await asyncio.sleep(0.5)
            log.info("live query queue shut down")



