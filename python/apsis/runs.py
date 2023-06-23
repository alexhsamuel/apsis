import asyncio
from   contextlib import contextmanager
import enum
import jinja2
import logging
import ora
from   ora import now, Time
import shlex

from   .lib.calendar import get_calendar
from   .lib.memo import memoize
from   .lib.py import format_ctor, iterize

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

    __slots__ = ("job_id", "args", )

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


    def to_jso(self):
        return [self.job_id, self.args]


    @classmethod
    def from_jso(cls, jso):
        job_id, args = jso
        return cls(job_id, args)



#-------------------------------------------------------------------------------

_get_template = memoize(jinja2.Template)

def template_expand(template, args):
    template = _get_template(str(template))
    return template.render(args)


def arg_to_bool(arg):
    if arg in ("true", "True"):
        return True
    elif arg in ("false", "False"):
        return False
    else:
        return bool(arg)


def join_args(argv):
    return " ".join( shlex.quote(a) for a in argv )


def propagate_args(old_args, job, new_args):
    """
    Propagates args from `old_args` to `new_args` if needed for `job`.

    Returns an arg dict, containing `new_args` plus any args that are missing
    for `job` but available in `old_args`.
    """
    args = { p: old_args[p] for p in job.params if p in old_args }
    args.update(new_args)
    return args


#-------------------------------------------------------------------------------

class Run:

    STATE = enum.Enum(
        "Run.STATE",
        (
            "new",
            "scheduled",
            "waiting",
            "starting",
            "running",
            "success",
            "failure",
            "error",
            "skipped",
        )
    )

    FINISHED = {STATE.success, STATE.failure, STATE.error, STATE.skipped}

    # State model.  Allowed transitions _to_ each state.
    TRANSITIONS = {
        STATE.new       : set(),
        STATE.scheduled : {STATE.new},
        STATE.waiting   : {STATE.new, STATE.scheduled},
        STATE.starting  : {STATE.scheduled, STATE.waiting},
        STATE.running   : {STATE.starting},
        STATE.error     : {STATE.new, STATE.scheduled, STATE.waiting, STATE.starting, STATE.running, STATE.skipped},
        STATE.success   : {STATE.running},
        STATE.failure   : {STATE.running},
        STATE.skipped   : {STATE.new, STATE.scheduled, STATE.waiting},
    }

    # FIXME: Make the attributes read-only.

    __slots__ = (
        "inst",
        "run_id",
        "timestamp",
        "state",
        "expected",
        "conds",
        "program",
        "times",
        "meta",
        "message",
        "run_state",
        "_jso_cache",
        "_rowid",
    )

    def __init__(self, inst, *, expected=False):
        """
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
        self.conds      = None
        self.program    = None
        # Timestamps for state transitions and other events.
        self.times      = {}
        # Additional run metadata.
        self.meta       = {}
        # User message explaining the state.
        self.message    = None
        # State information specific to the program, for a running run.
        self.run_state  = None

        # Cached summary JSO object.
        self._jso_cache = None


    def __hash__(self):
        return hash(self.run_id)


    def __eq__(self, other):
        return other.run_id == self.run_id


    def __repr__(self):
        return format_ctor(self, self.run_id, self.inst, state=self.state)


    def __str__(self):
        return f"{self.run_id} {self.state.name} {self.inst}"


    def _transition(self, timestamp, state, *, meta={}, times={},
                    message=None, run_state=None, force=False):
        """
        :param force:
          Transition outside of the state model.
        """
        # Check that this is a valid transition.
        if not force and self.state not in self.TRANSITIONS[state]:
            raise TransitionError(self.state, state)

        assert all( isinstance(t, Time) and t.valid for t in times.values() )

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
            self.meta["elapsed"] = elapsed

        # Transition to the new state.
        self.state = state

        # Discard cached JSO.  Used by run_summary_to_json().
        self._jso_cache = None



#-------------------------------------------------------------------------------

BIND_ARGS = {
    **{
        n: getattr(ora, n)
        for n in (
                "Date",
                "Daytime",
                "Time",
                "TimeZone",
                "to_local",
                "from_local",
        )
    },
    "format": format,
    "get_calendar": get_calendar,
}

def get_bind_args(run):
    """
    Returns args available to template expansion for `run`.
    """
    return {
        **BIND_ARGS,
        "run_id": run.run_id,
        "job_id": run.inst.job_id,
        **run.inst.args,
    }


#-------------------------------------------------------------------------------

class _RunsFilter:
    """
    Filter predicate for an iterable of runs.
    """

    def __init__(
            self, *,
            run_ids=None,
            job_id=None,
            state=None,
            since=None,
            args=None,
            with_args=None,
    ):
        """
        :param state:
          Limits results to runs in the specified state(s).
        :param args:
          Limits results to runs with exactly the specified args.
        :param with_args:
          Limits results to runs with the specified args.  Runs may include
          other args not explicitly given.
        """
        to_map = lambda x: { str(k): str(v) for k, v in x.items() }
        self.run_ids    = None if run_ids   is None else set(iterize(run_ids))
        self.job_id     = None if job_id    is None else job_id
        self.state      = None if state     is None else set(iterize(state))
        self.since      = None if state     is None else ora.Time(since)
        self.args       = None if args      is None else to_map(args)
        self.with_args  = None if with_args is None else to_map(with_args)


    def __call__(self, runs):
        if self.run_ids is not None:
            run_ids = self.run_ids
            runs = ( r for r in runs if r.run_id in run_ids )

        if self.job_id is not None:
            job_id = self.job_id
            runs = ( r for r in runs if r.inst.job_id == job_id )

        if self.state is not None:
            state = self.state
            runs = ( r for r in runs if r.state in state )

        if self.since is not None:
            since = self.since
            runs = ( r for r in runs if r.timestamp >= since )

        if self.args is not None:
            args = self.args
            runs = ( r for r in runs if r.inst.args == args )

        if self.with_args is not None:
            with_args = self.with_args
            runs = (
                r for r in runs
                if all(
                        r.inst.args.get(k, None) == v
                        for k, v in with_args.items()
                )
            )

        return runs



#-------------------------------------------------------------------------------

class RunStore:
    """
    Stores runs in memory.

    This is a cache, backed by a write-through persistent run database.  New
    runs are always added to the cache; use `retire()` to retire older runs from
    memory.

    - Stories runs in all states.
    - Satisfyies run queries.
    - Serves live queries of runs.
    """

    def __init__(self, db, *, min_timestamp):
        self.__run_db = db.run_db
        self.__next_run_id_db = db.next_run_id_db

        # Populate cache from database.
        self.__runs = {
            r.run_id: r
            for r in self.__run_db.query(min_timestamp=min_timestamp)
        }
        # Also keep a lookup of runs by job ID.
        self.__runs_by_job = {
            r.inst.job_id: {r}
            for r in self.__runs.values()
        }

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
        run_id = self.__next_run_id_db.get_next_run_id()
        assert run.run_id not in self.__runs

        run.run_id = run_id
        run.timestamp = timestamp

        log.debug(f"new run: {run}")
        self.__runs[run.run_id] = run
        self.__runs_by_job.setdefault(run.inst.job_id, set()).add(run)
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

        # Persist the changes, but not for expected runs.
        if not run.expected:
            self.__run_db.upsert(run)

        self.__send(timestamp, run)


    def remove(self, run_id):
        """
        Removes run with `run_id`.

        Only an expected run may be removed.
        """
        run = self.__runs[run_id]
        assert run.expected, f"can't remove run {run_id}; not expected"

        del self.__runs[run_id]
        self.__runs_by_job[run.inst.job_id].remove(run)
        # Indicate deletion with none state.
        # FIXME: What a horrible hack.
        run.state = None
        self.__send(now(), run)
        return run


    def retire(self, run_id):
        """
        :return:
          True if `run_id` is not in the store, either because it was
          successfully retired, or because it wasn't there to begin with.
        """
        try:
            run = self.__runs[run_id]
        except KeyError:
            return True
        else:
            if run.state in Run.FINISHED:
                self.__runs.pop(run_id)
                self.__runs_by_job[run.inst.job_id].remove(run)
                run.state = None
                self.__send(now(), run)
                return True
            else:
                return False


    def retire_old(self, min_timestamp):
        """
        Retires older runs from memory.

        Only runs in a finished state are retired.  Runs are not removed from
        the database.
        """
        old = [
            r for r in self.__runs.values()
            if r.timestamp < min_timestamp
        ]
        count = sum( self.retire(r.run_id) for r in old )
        log.info(f"retired {count} runs before {min_timestamp}")


    def __contains__(self, run_id):
        return run_id in self.__runs


    def get(self, run_id):
        run = self.__runs[run_id]
        return now(), run


    def _query_filter(self, filter):
        """
        Queries using a `_RunsFilter`.
        """
        assert filter.run_ids is None or filter.job_id is None

        if filter.run_ids is not None:
            # Fast path if the query is by run IDs.
            runs = ( self.__runs.get(i, None) for i in filter.run_ids )
            runs = ( r for r in runs if r is not None )
        elif filter.job_id is not None:
            # Fast path if the query is by job ID.
            runs = iter(self.__runs_by_job.get(filter.job_id, ()))
        else:
            # Slow path: scan.
            runs = self.__runs.values()

        return now(), list(filter(runs))


    def query(self, **filter_args):
        """
        :keywords:
          See `_RunsFilter.__init__.
        """
        return self._query_filter(_RunsFilter(**filter_args))


    @contextmanager
    def query_live(self, **filter_args):
        """
        :keywords:
          See `_RunsFilter.__init__.
        """
        queue = asyncio.Queue()
        self.__queues.add(queue)
        log.info("added live runs query queue")

        filter = _RunsFilter(**filter_args)
        when, runs = self._query_filter(filter)
        queue.put_nowait((when, runs))

        # FIXME: Apply filter to queue.

        try:
            yield queue
        finally:
            self.__queues.remove(queue)
            log.info("removed live runs query queue")


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



#-------------------------------------------------------------------------------

def to_state(state):
    if isinstance(state, Run.STATE):
        return state
    try:
        return Run.STATE[state]
    except KeyError:
        pass
    raise ValueError(f"not a state: {state!r}")
