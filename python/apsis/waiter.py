import asyncio
import logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Waiter:
    """
    Holds runs in the waiting state until all conditions are satisfied.
    """

    # FIXME: Primitive first cut: just store all runs with their blockers,
    # by run ID, and reevaluate all of them every time.

    def __init__(self, runs, start, run_history):
        self.__runs = runs
        self.__start = start
        self.__run_history = run_history

        # Mapping from run ID to (run, conds).  The latter is a list of 
        # conds that have not yet been checked.  The first cond is blocking.
        # Others may not have been checked yet.  The list is mutated as conds
        # are checked.
        self.__waiting = {}


    def __check(self, run, conds):
        """
        Checks conditions for a blocker, starting from the front. 

        On return, either `conds` is empty and the run is not blocked, or the
        run is blocked on `conds[0]`.

        :param conds:
          A list of conditions; mutated.
        """
        while len(conds) > 0:
            if conds[0].check_runs(self.__runs):
                # Not blocking.
                conds.pop(0)
            else:
                # Blocking.
                break


    async def start(self, run):
        """
        Starts `run`, unless it's blocked; if so, registers it to wait for.
        """
        conds = list(run.conds)
        self.__check(run, conds)

        if len(conds) == 0:
            # Ready to run.
            log.debug(f"starting: {run}")
            await self.__start(run)

        else:
            # Blocked by a cond.
            assert run.run_id not in self.__waiting
            self.__run_history.info(run, f"waiting for {conds[0]}")
            self.__waiting[run.run_id] = (run, conds)


    async def __check_all(self):
        """
        Checks conds on all waiting runs; starts any no longer blocked.
        """
        for run_id, (run, conds) in list(self.__waiting.items()):
            last_blocker = conds[0]
            self.__check(run, conds)

            if len(conds) == 0:
                # No longer blocked; ready to run.
                self.__run_history.info(run, f"no longer waiting")
                del self.__waiting[run.run_id]
                await self.__start(run)

            else:
                # Still blocked.
                blocker = conds[0]
                if blocker is not last_blocker:
                    # Blocked by a new cond.
                    self.__run_history.info(run, f"waiting for {blocker}")


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



