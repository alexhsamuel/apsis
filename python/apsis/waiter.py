import asyncio
import logging

from   .lib.json import Typed, no_unexpected_keys
from   .runs import Run, template_expand

log = logging.getLogger(__name__)

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
    def from_jso(Class, jso):
        return Class(
            jso.pop("count", 1),
            jso.pop("job_id", None),
            jso.pop("args", None),
        )


    def bind(self, args, inst):
        count = int(template_expand(self.__count, args))
        return type(self)(count, inst.job_id, inst.args)


    def check_runs(self, runs):
        # FIXME: Support query by args.
        _, running = runs.query(
            job_id=self.__job_id, 
            state=Run.STATE.running,
        )
        for name, val in self.__args.items():
            running = ( r for r in running if r.inst.args.get(name) == val )
        count = len(list(running))
        log.debug(f"count matching {self.__job_id} {self.__args}: {count}")
        return count < self.__count



TYPES = Typed({
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
        log.debug(f"check all: {len(self.__waiting)} runs")
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
        log.debug(f"check all done: {len(self.__waiting)} runs left")


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



