import asyncio
import logging
import ora

from   .exc import TimeoutWaiting

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

async def wait_loop(apsis, run, cfg):
    """
    Waits for all conds to be met.
    """
    conds = list(run.conds)

    max_time = cfg.get("max_time", None)
    if max_time is None:
        timeout = None
    else:
        try:
            start = ora.Time(run.times["waiting"])
        except KeyError:
            log.error(f"waiting run missing waiting time: {run.run_id}")
            # Fall back to current time.
            start = ora.now()
        timeout = start + max_time

    if len(conds) > 0:
        apsis.run_log.info(run, f"waiting for {conds[0]}")

        while len(conds) > 0:
            cond = conds[0]
            if (
                    # FIXME: In the future, we won't poll run conditions, but
                    # rather check only on run transitions.
                    cond.check_runs(apsis.run_store)
                    and await cond.check()
            ):
                apsis.run_log.info(run, f"satisfied {cond}")
                conds.pop(0)
                if len(conds) > 0:
                    apsis.run_log.info(run, f"waiting for {conds[0]}")
            else:
                # First cond is still blocking.
                if timeout is not None:
                    # Check for timeout while waiting.
                    now = ora.now()
                    remaining = timeout - now
                    if 0 < remaining:
                        sleep_time = min(cond.poll_interval, remaining)
                    else:
                        raise TimeoutWaiting(
                            f"time out waiting after {max_time} sec")
                else:
                    sleep_time = cond.poll_interval

                await asyncio.sleep(sleep_time)

        else:
            apsis.run_log.info(run, "all conditions satisfied")


