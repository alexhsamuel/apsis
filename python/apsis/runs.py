from   collections import namedtuple
import jinja2
import logging
import ora
from   ora import now, Time
import shlex

from   .states import State, TRANSITIONS
from   .lib.asyn import Publisher
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

class _Undefined(jinja2.StrictUndefined):
    """
    Custom Jinja2 undefined type that throws `NameError`.
    """

    def __init__(self, *args, **kw_args):
        super().__init__(*args, **kw_args)
        self._undefined_exception = NameError



_JINJA_ENV = jinja2.Environment(
    undefined   =_Undefined,
)

@memoize
def _get_template(template):
    try:
        return _JINJA_ENV.from_string(template)
    except jinja2.TemplateSyntaxError as exc:
        raise SyntaxError(str(exc))


def template_expand(template, args):
    """
    Expands Jinja2-style `template` with names from `args`.

    :raise SyntaxError:
      The template doesn't conform to Jinja2 syntax.
    :raise NameError:
      The template references a name not in `args`.
    """
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
        "_summary_jso_cache",
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

        self.state      = State.new
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
        self._summary_jso_cache = None


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
        :param meta:
          Metadata updates.  Sets or replaces run metadata keys from this
          mapping.
        """
        # Check that this is a valid transition.
        if not force and self.state not in TRANSITIONS[state]:
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
        self._summary_jso_cache = None



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

class _RunPredicate:
    """
    Filter predicate for a run.
    """

    def __init__(
            self, *,
            run_ids     =None,
            job_id      =None,
            state       =None,
            since       =None,
            args        =None,
            with_args   =None,
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


    def __call__(self, run):
        return (
                (self.run_ids   is None or run.run_id in self.run_ids)
            and (self.job_id    is None or run.inst.job_id == self.job_id)
            and (self.state     is None or run.state in self.state)
            and (self.since     is None or run.timestamp >= self.since)
            and (self.args      is None or run.inst.args == self.args)
            and (self.with_args is None or all(
                run.inst.args.get(k) == v
                for k, v in self.with_args.items()
            ))
        )



#-------------------------------------------------------------------------------

class RunStore:
    """
    Stores runs in memory.

    This is a cache, backed by a write-through persistent run database.  New
    runs are always added to the cache; use `retire()` to retire older runs from
    memory.

    - Stores runs in all states.
    - Satisfyies run queries.
    """

    Message = namedtuple("Message", ("run_id", "job_id", "args", "state"))

    def __init__(self, db, *, min_timestamp):
        self.__run_db = db.run_db
        self.__next_run_id_db = db.next_run_id_db

        # Populate cache from database.
        self.__runs = {
            r.run_id: r
            for r in self.__run_db.query(min_timestamp=min_timestamp)
        }
        # Keep a lookup of runs by job ID.
        self.__runs_by_job = {}
        for run in self.__runs.values():
            self.__runs_by_job.setdefault(run.inst.job_id, set()).add(run)

        # Publisher for run transitions.  Messages are `Message` objects;
        # `state` is none if the run is removed.
        self.publisher = Publisher()


    def add(self, run):
        assert run.state == State.new

        timestamp = now()
        run_id = self.__next_run_id_db.get_next_run_id()
        assert run.run_id not in self.__runs

        run.run_id = run_id
        run.timestamp = timestamp

        log.debug(f"new run: {run}")
        self.__runs[run.run_id] = run
        self.__runs_by_job.setdefault(run.inst.job_id, set()).add(run)
        self.update(run, timestamp)
        self.publisher.publish(
            self.Message(run.run_id, run.inst.job_id, run.inst.args, run.state))


    # FIXME: Remove timestamp.
    def update(self, run, timestamp):
        """
        Called when `run` is changed.

        Persists the run if necessary.
        """
        # Make sure we know about this run.
        assert self.__runs[run.run_id] is run

        # Persist the changes, but not for expected runs.
        if not run.expected:
            self.__run_db.upsert(run)

        # FIXME: Separate transition() so we don't send this on updates.
        self.publisher.publish(
            self.Message(run.run_id, run.inst.job_id, run.inst.args, run.state))


    def remove(self, run_id, *, expected=True):
        """
        Removes run with `run_id`.

        :param expected:
          If true, only an expected run may be removed.
        """
        run = self.__runs[run_id]
        assert not expected or run.expected, f"can't remove run {run_id}; not expected"

        del self.__runs[run_id]
        self.__runs_by_job[run.inst.job_id].remove(run)
        self.publisher.publish(
            self.Message(run.run_id, run.inst.job_id, run.inst.args, None))
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
            if run.state.finished:
                self.remove(run_id, expected=False)
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


    # FIXME: Merge down.
    def _query_filter(self, predicate):
        """
        Queries using a `_RunPredicate`.
        """
        if predicate.run_ids is not None:
            # Fast path if the query is by run IDs.
            runs = (
                r
                for i in predicate.run_ids
                if (r := self.__runs.get(i)) is not None
            )
        elif predicate.job_id is not None:
            # Fast path if the query is by job ID.
            runs = iter(self.__runs_by_job.get(predicate.job_id, ()))
        else:
            # Slow path: scan.
            runs = self.__runs.values()

        return now(), [ r for r in runs if predicate(r) ]


    # FIXME: Remove `when` from the result; I think we don't use it.
    def query(self, **filter_args):
        """
        :keywords:
          See `_RunPredicate.__init__.
        """
        return self._query_filter(_RunPredicate(**filter_args))


    def get_stats(self):
        return {
            "num_runs"      : len(self.__runs),
            "publisher"     : self.publisher.get_stats(),
        }



