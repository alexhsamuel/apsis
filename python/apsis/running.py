"""
Managing runs in the _running_ state.
"""

import asyncio
import logging
from   ora import now
import traceback

from   apsis.lib.cmpr import compress_async
from   apsis.program.base import (
    Output, OutputMetadata,
    ProgramRunning, ProgramError, ProgramFailure, ProgramSuccess, ProgramUpdate)
from   apsis.states import State

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

async def _maybe_compress(outputs, *, compression="br", min_size=16384):
    """
    Compresses final outputs, if needed.
    """
    async def _cmpr(output):
        if output.compression is None and output.metadata.length >= min_size:
            # Compress the output.
            try:
                compressed = await compress_async(output.data, compression)
            except RuntimeError as exc:
                log.error(f"{exc}; not compressiong")
                return output
            else:
                return Output(output.metadata, compressed, compression)
        else:
            return output

    o = await asyncio.gather(*( _cmpr(o) for o in outputs.values() ))
    return dict(zip(outputs.keys(), o))


async def _process_updates(apsis, run, updates, program):
    """
    Processes program `updates` for `run` until the program is finished.
    """
    run_id = run.run_id
    updates = aiter(updates)

    try:
        if run.state == State.starting:
            update = await anext(updates)
            match update:
                case ProgramRunning() as running:
                    apsis.run_log.record(run, "running")
                    apsis._transition(
                        run, State.running,
                        run_state   =running.run_state,
                        meta        ={"program": running.meta},
                        times       =running.times,
                    )

                case ProgramError() as error:
                    apsis.run_log.info(run, f"error: {error.message}")
                    apsis._update_output_data(run, error.outputs, persist=True)
                    apsis._transition(
                        run, State.error,
                        meta        ={"program": error.meta},
                        times       =error.times,
                    )
                    return

                case _ as update:
                    assert False, f"unexpected update: {update}"

        assert run.state == State.running

        # Does this run have a scheduled stop time?
        try:
            stop_time = run.times["stop"]
        except KeyError:
            stop_task = None
        else:
            # Start a task to stop the run at the scheduled time.
            async def stop():
                duration = stop_time - now()
                log.debug(f"{run_id}: running for {duration} s until stop")
                await asyncio.sleep(duration)
                log.debug(f"{run_id}: stopping")
                await program.stop()

            stop_task = asyncio.create_task(stop())

        while run.state == State.running:
            update = await anext(updates)
            match update:
                case ProgramUpdate() as update:
                    if update.outputs is not None:
                        apsis._update_output_data(run, update.outputs, False)
                    if update.meta is not None:
                        apsis._update_metadata(run, {"program": update.meta})

                case ProgramSuccess() as success:
                    apsis.run_log.record(run, "success")
                    apsis._update_output_data(
                        run,
                        await _maybe_compress(success.outputs),
                        True
                    )
                    apsis._transition(
                        run, State.success,
                        meta        ={"program": success.meta},
                        times       =success.times,
                    )

                case ProgramFailure() as failure:
                    # Program ran and failed.
                    apsis.run_log.record(run, f"failure: {failure.message}")
                    apsis._update_output_data(
                        run,
                        await _maybe_compress(failure.outputs),
                        True
                    )
                    apsis._transition(
                        run, State.failure,
                        meta        ={"program": failure.meta},
                        times       =failure.times,
                    )

                case ProgramError() as error:
                    apsis.run_log.info(run, f"error: {error.message}")
                    apsis._update_output_data(
                        run,
                        await _maybe_compress(error.outputs),
                        True
                    )
                    apsis._transition(
                        run, State.error,
                        meta        ={"program": error.meta},
                        times       =error.times,
                    )

                case _ as update:
                    assert False, f"unexpected update: {update}"

        else:
            # Cancel the stop task.
            if stop_task is not None:
                stop_task.cancel()

            # Exhaust the async iterator, so that cleanup can run.
            try:
                update = await anext(updates)
            except StopAsyncIteration:
                # Expected.
                pass
            else:
                assert False, f"unexpected update: {update}"

    except (asyncio.CancelledError, StopAsyncIteration):
        # We do not transition the run here.  The run can survive an Apsis
        # restart and we can connect to it later.
        pass

    except Exception:
        # Program raised some other exception.
        apsis.run_log.exc(run, "error: internal")
        tb = traceback.format_exc().encode()
        output = Output(OutputMetadata("traceback", length=len(tb)), tb)
        apsis._update_output_data(run, {"outputs": output}, True)
        apsis._transition(run, State.error)


