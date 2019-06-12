import asyncio
import logging

from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import iterize
from   .runs import Run, Instance, get_bind_args, template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere?

def _bind(params, obj_args, inst_args, bind_args):
    """
    Binds args to `params`.

    Binds `obj_args` and `inst_args` to params by name.  `obj_args` take
    precedence, and are template-expanded with `bind_args`; `inst_args` are
    not expanded.
    """
    def get(name):
        try:
            return template_expand(obj_args[name], bind_args)
        except KeyError:
            pass
        try:
            return inst_args[name]
        except KeyError:
            pass
        raise LookupError(f"no value for param {name}")

    return { n: get(n) for n in params }


#-------------------------------------------------------------------------------

class Preco:
    """
    Precondition type.  Not a base class; for API illustration only.
    """

    def to_jso(self):
        pass


    @classmethod
    def from_jso(Class, jso):
        pass


    def bind(self, run, jobs):
        """
        Binds a job preco to `inst`.

        :param run:
          The run to bind to.
        :param jobs:
          The jobs DB.
        :return:
          An instance of the same preco type, bound to the instances.
        """


    def check_runs(self, runs):
        """
        Checks whether all run precos are met.

        :param runs:
          The run DB.
        :return:
          True if dependencies are met.
        """



#-------------------------------------------------------------------------------

class MaxRunningPreco:

    def __init__(self, count, job_id=None, args=None):
        """
        :param job_id:
          Job ID of runs to count.  If none, bound to the job ID of the 
          owning instance.
        :param args:
          Args to match.  If none, the bound to the args of the owning instance.
        """
        self.__count = count
        self.__job_id = job_id
        self.__args = args


    def to_jso(self):
        return {
            "count" : self.__count,
            "job_id": self.__job_id,
             "args" : self.__args,
        }


    @classmethod
    def from_jso(cls, jso):
        return cls(
            jso.pop("count", "1"),
            jso.pop("job_id", None),
            jso.pop("args", None),
        )


    def bind(self, run, jobs):
        bind_args = get_bind_args(run)
        count = template_expand(self.__count, bind_args)
        job_id = run.inst.job_id if self.__job_id is None else self.__job_id
        # FIXME: Support self.__args not none.  Template-expand them, add in
        # inst.args, and bind to job args.
        if self.__args is not None:
            raise NotImplementedError()
        return type(self)(count, job_id, run.inst.args)


    def check_runs(self, runs):
        max_count = int(self.__count)

        # FIXME: Support query by args.
        _, running = runs.query(
            job_id=self.__job_id, 
            state=Run.STATE.running,
        )
        for name, val in self.__args.items():
            running = ( r for r in running if r.inst.args.get(name) == val )
        count = len(list(running))
        log.debug(f"count matching {self.__job_id} {self.__args}: {count}")
        return count < max_count



#-------------------------------------------------------------------------------

class Dependency:

    def __init__(self, job_id, args, states={Run.STATE.success}):
        states = list(iterize(states))
        assert all( isinstance(s, Run.STATE) for s in states )

        self.job_id = job_id
        self.args = args
        self.states = states


    def to_jso(self):
        return {
            "job_id": self.job_id,
            "args"  : self.args,
            "states": [ s.name for s in self.states ],
        }


    @classmethod
    def from_jso(cls, jso):
        states = { Run.STATE[s] for s in iterize(jso.pop("states", "success")) }
        return cls(
            jso.pop("job_id"),
            jso.pop("args", {}),
            states,
        )


    def bind(self, run, jobs):
        job = jobs[self.job_id]
        bind_args = get_bind_args(run)
        args = _bind(job.params, self.args, run.inst.args, bind_args)
        return type(self)(self.job_id, args, self.states)


    # FIXME: Handle exceptions when checking.

    def check_runs(self, runs):
        # FIXME: Support query by args.
        # FIXME: Support query by multiple states.
        for state in self.states:
            _, deps = runs.query(job_id=self.job_id, state=state)
            for dep in deps:
                if dep.inst.args == self.args:
                    log.debug(f"dep satisfied: {dep}")
                    return True
        else:
            inst = Instance(self.job_id, self.args)
            log.debug(f"dep not satisified: {inst}")
            return False



#-------------------------------------------------------------------------------

TYPES = Typed({
    "dependency"        : Dependency,
    "max_running"       : MaxRunningPreco,
})

def preco_from_jso(jso):
    with no_unexpected_keys(jso):
        return TYPES.from_jso(jso)


preco_to_jso = TYPES.to_jso

#-------------------------------------------------------------------------------

class Waiter:

    def __init__(self, runs, start):
        self.__runs = runs
        self.__start = start

        # FIXME: Primitive first cut: just store all runs with their blockers,
        # and reevaluate all of them every time.
        self.__waiting = []


    async def start(self, run):
        """
        Starts `run`, unless it's blocked; if so, wait for it.
        """
        # Find which precos are blocking the run.
        blockers = [ p for p in run.precos if not p.check_runs(self.__runs) ]

        if len(blockers) == 0:
            # Ready to run.
            log.debug(f"starting: {run}")
            await self.__start(run)
        else:
            self.__waiting.append((run, blockers))


    def wait_for(self, run):
        """
        Adds `run` to the list of runs to await.

        If the run is not blocked, it will be started on the next waiter loop.
        """
        # Find which precos are blocking the run.
        blockers = [ p for p in run.precos if not p.check_runs(self.__runs) ]

        self.__waiting.append((run, blockers))


    async def __check_all(self):
        waiting = []
        for run, blockers in self.__waiting:
            while len(blockers) > 0:
                if blockers[0].check_runs(self.__runs):
                    # This preco no longer blocking.
                    log.debug(f"{run.run_id}: {blockers[0]} no longer blocking")
                    blockers.pop(0)
                else:
                    log.debug(f"{run.run_id}: {blockers[0]} still blocking")
                    break
            if len(blockers) > 0:
                # Still blocked.
                log.debug(f"{run.run_id} still blocked")
                waiting.append((run, blockers))
            else:
                # No longer blocked; ready to run.
                log.debug(f"{run.run_id} starting")
                await self.__start(run)

        self.__waiting = waiting


    async def loop(self):
        """
        Waits for waiting runs to become ready.
        """
        # FIXME
        try:
            while True:
                await self.__check_all()
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            # Let this through.
            pass

        except Exception:
            # FIXME: Do this in Apsis.
            log.critical("waiter loop failed", exc_info=True)
            raise SystemExit(1)



