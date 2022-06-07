import asyncio
import logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

async def wait_loop(apsis, run):
    """
    Waits for all conds to be met.
    """
    conds = list(run.conds)

    if len(conds) > 0:
        apsis.run_log.info(run, f"waiting for {conds[0]}")

        while len(conds) > 0:
            cond = conds[0]
            if cond.check_runs(apsis.run_store):
                apsis.run_log.info(run, f"satisfied {cond}")
                conds.pop(0)
                if len(conds) > 0:
                    apsis.run_log.info(run, f"waiting for {conds[0]}")
            else:
                # First cond is still blocking.
                await asyncio.sleep(1)

        else:
            apsis.run_log.info(run, "all conditions satisfied")


