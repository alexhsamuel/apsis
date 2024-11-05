import asyncio
from   functools import partial
import logging
import math
from   mmap import PAGESIZE
from   ora import now, Time
import resource
import sys
import traceback

from   . import procstar
from   .actions import Action
from   .cond.base import PolledCondition, RunStoreCondition, NonmonotonicRunStoreCondition
from   .host_group import config_host_groups
from   .jobs import Jobs, load_jobs_dir, diff_jobs_dirs
from   .lib.api import run_to_summary_jso
from   .lib.asyn import TaskGroup, Publisher, KeyPublisher
from   .lib.cmpr import compress_async
from   .lib.sys import to_signal
from   .output import OutputStore
from   .program.base import _InternalProgram
from   .program.base import Output, OutputMetadata
from   .program.base import ProgramRunning, ProgramError, ProgramFailure, ProgramSuccess, ProgramUpdate
from   . import runs
from   .run_log import RunLog
from   .run_snapshot import snapshot_run
from   .runs import Run, RunStore, RunError, MissingArgumentError, ExtraArgumentError
from   .runs import validate_args, bind
from   .scheduled import ScheduledRuns
from   .scheduler import Scheduler, get_insts_to_schedule
from   .service import messages
from   .states import State

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Apsis:
    """
    The gestalt scheduling application.

    Responsible for:

    - Assembling subcomponents:
      - job repo
      - persistent database
      - scheduler
      - scheduled

    - Managing run transitions:
      - handing runs from one component to the next
      - applying and persisting transitions

    - Exposing a high-level API for user run operations

    """

    def __init__(self, cfg, jobs, db):
        self.__start_time = now()

        # False while starting, set to true once up and running.
        self.running_flag = asyncio.Event()

        # Set up groups of tasks, starting with the general group.
        self.__tasks = TaskGroup(log)
        # One task for each waiting run.
        self.__wait_tasks = TaskGroup(log)
        # One task for each starting/running run.
        self.__run_tasks = TaskGroup(log)
        # One task for each running action.
        self.__action_tasks = TaskGroup(log)

        self.cfg = cfg
        # FIXME: This should go in `apsis.config.config_globals` or similar.
        config_host_groups(cfg)
        self.__db = db

        # Publisher for summary updates.
        self.summary_publisher = Publisher()
        # Publisher for per-run updates.
        self.run_update_publisher = KeyPublisher()
        # Publisher for output data updates.
        self.output_update_publisher = KeyPublisher()

        self.run_log = RunLog(self.__db.run_log_db, self.run_update_publisher)
        self.jobs = Jobs(jobs, db.job_db)

        # Actions applied to all runs.
        self.__actions = [ Action.from_jso(o) for o in cfg["actions"] ]

        # Calculate how far back we should load runs into the run store.
        try:
            lookback = cfg["runs"]["lookback"]
        except KeyError:
            min_timestamp = None
        else:
            min_timestamp = now() - lookback
        self.run_store = RunStore(db, min_timestamp=min_timestamp)

        # Previously we didn't serialize conds or actions.  Bind them if
        # missing on loaded runs.
        # FIXME: Remove this after a while.
        for run in self.run_store.query()[1]:
            try:
                job = self.job.get_job(run.inst.job_id)
                bind(run, job, self.jobs)
            except Exception:
                log.error(f"failed to bind run from job: {run}")

        self.outputs = OutputStore(db.output_db)

        # Continue scheduling from the last time we handled scheduled jobs.
        # FIXME: Rename: schedule horizon?
        stop_time = db.clock_db.get_time()
        self.scheduler = Scheduler(
            cfg,
            self.jobs,
            # All runs scheduled by the scheduler are expected.
            partial(self.schedule, expected=True),
            stop_time
        )

        self.scheduled = ScheduledRuns(db.clock_db, self.scheduler.get_scheduler_time, self._wait)

        # Stats from the async check loop.
        self.__check_async_stats = {}

        # False while starting, set to true once up and running.
        self.running_flag = asyncio.Event()


    async def restore(self):
        """
        Restores scheduled, waiting, and running runs from DB.
        """
        try:
            log.info("restoring")

            # Restore scheduled runs from DB.
            log.info("restoring scheduled runs")
            _, scheduled_runs = self.run_store.query(state=State.scheduled)
            for run in scheduled_runs:
                assert not run.expected
                time = run.times["schedule"]
                self.run_log.record(run, "restored")
                await self.scheduled.schedule(time, run)

            # Restore waiting runs from DB.
            log.info("restoring waiting runs")
            _, waiting_runs = self.run_store.query(state=State.waiting)
            for run in waiting_runs:
                assert not run.expected
                self.run_log.record(run, "restored")
                self._wait(run)

            # If a run is starting in the DB, we can't know if it actually
            # started or not, so mark it as error.
            log.info("processing starting runs")
            _, starting_runs = self.run_store.query(state=State.starting)
            for run in starting_runs:
                self.run_log.record(run, "restored starting: might have started")
                self._transition(run, State.error)

            # Reconnect to running runs.
            _, running_runs = self.run_store.query(state=State.running)
            log.info("reconnecting running runs")
            for run in running_runs:
                self.__reconnect(run)

            log.info("restoring done")

        except Exception:
            log.critical("restore failed", exc_info=True)
            raise SystemExit(1)


    # FIXME: Rename to start?
    def start_loops(self):
        # Start a loop to monitor the async event loop.
        self.__tasks.add("check_async", self.__check_async())

        # Set up the scheduler.
        log.info("starting scheduler loop")
        self.__tasks.add("scheduler_loop", self.scheduler.loop())

        # Set up the manager for scheduled tasks.
        log.info("starting scheduled loop")
        self.__tasks.add("scheduled_loop", self.scheduled.loop())

        # Start the Procstar agent server, if enabled.
        procstar_cfg = self.cfg.get("procstar", {}).get("agent", {})
        if procstar_cfg.get("enable", False):
            log.info("starting procstar server")
            run_agent_server = procstar.start_agent_server(procstar_cfg)
            self.__tasks.add("agent_conn", procstar.agent_conn(self))
            self.__tasks.add("agent_server", run_agent_server)

        # Start a task to retire old runs.
        self.__tasks.add("retire_loop", _retire_loop(self))

        # We're running now.
        self.running_flag.set()


    def _wait(self, run):
        """
        Starts waiting for `run`.
        """
        if len(run.conds) == 0:
            # No conditions to wait for.  Start immediately.
            self._start(run)
            return

        # Make sure the run is waiting.
        if run.state != State.waiting:
            self.run_log.record(run, "waiting")
            self._transition(run, State.waiting)

        timeout = self.cfg.get("waiting", {}).get("max_time", None)

        # Start the waiting task.
        self.__wait_tasks.add(run.run_id, _wait_loop(self, run, timeout))


    def _start(self, run):
        """
        Starts a run.

        Runs the run's program in a task added to `__run_tasks`.
        """
        # Start the run by running its program.
        self.run_log.record(run, "starting")
        self._transition(run, State.starting)
        # Call the program.  This produces an async iterator of updates.
        updates = run.program.run(
            run.run_id,
            self if isinstance(run.program, _InternalProgram) else self.cfg,
        )
        # Start a task to process updates from the program.
        run_task = _process_updates(self, run, updates)
        self.__run_tasks.add(run.run_id, run_task)


    def __reconnect(self, run):
        """
        Reconnects to a running run.

        Finishes running the run's program in a task added to `__run_tasks`.
        """
        assert run.state == State.running
        assert run.run_state is not None
        self.run_log.record(run, "reconnecting")
        # Connect to the program.  This produces an async iterator of updates.
        updates = run.program.connect(
            run.run_id,
            run.run_state,
            self if isinstance(run.program, _InternalProgram) else self.cfg,
        )
        # Start a task to process updates from the program.
        run_task = _process_updates(self, run, updates)
        self.__run_tasks.add(run.run_id, run_task)


    def __start_actions(self, run):
        """
        Starts configured actions on `run` as tasks.
        """
        # Find actions attached to the job.
        actions = [] if run.actions is None else list(run.actions)
        # Include actions configured globally for all runs.
        actions += self.__actions

        # Check conditions on actions.
        actions = [
            a for a in actions
            if a.condition is None or a.condition(run)
        ]

        if len(actions) == 0:
            # Nothing to do.
            return

        async def wrap(run, snapshot, action):
            """
            Wrapper to handle exceptions from an action.

            Since these are run as background tasks, we don't transition the
            run to error if an action fails.
            """
            try:
                await action(self, snapshot)
            except Exception:
                self.run_log.exc(run, "action")

        # The actions run in tasks and the run may transition again soon, so
        # hand the actions a snapshot instead.
        snapshot = snapshot_run(self, run)

        for action in actions:
            key = (id(action), run.run_id, run.state)
            self.__action_tasks.add(key, wrap(run, snapshot, action))


    # --- Internal API ---------------------------------------------------------

    def _run_exc(self, run, *, message=None):
        """
        Transitions `run` to error, with the current exception attached.
        """
        self.run_log.exc(run, message)

        if run.state == State.error:
            # Already hit another error...
            return

        exc_type, exc, _ = sys.exc_info()
        if exc_type is not None:
            # Attach the exception traceback as run output.
            if issubclass(exc_type, RuntimeError):
                msg = str(exc).encode()
            else:
                msg = traceback.format_exc().encode()
            output = Output(
                OutputMetadata("output", len(msg), content_type="text/plain"),
                msg
            )
            # FIXME: For now, use the name "output" as this is the only one
            # the UIs render.  In the future, change to "traceback".
            self._update_output_data(run, {"output": output}, persist=True)

        self._transition(run, State.error, times={"error": now()})


    # FIXME: persist is a hack.
    def _update_metadata(self, run, meta):
        """
        Updates run metadata, without transitioning.
        """
        assert run.state in {State.starting, State.running}

        if meta is None or len(meta) == 0:
            return

        run.meta.update(meta)
        # Persist the new state.
        self.run_store.update(run, now())
        # Publish to run update subscribers.
        self.run_update_publisher.publish(run.run_id, {"meta": run.meta})


    def _update_output_data(self, run, outputs, persist):
        """
        Updates output data, without transitioning.

        :param persist:
          If true, write through to database; else cache in memory.
        """
        run_id = run.run_id

        # Persist outputs.
        write = self.outputs.write_through if persist else self.outputs.write
        for output_id, output in outputs.items():
            write(run_id, output_id, output)

        # Publish to run update subscribers.
        if run_id in self.run_update_publisher:
            msg = { i: o.metadata.to_jso() for i, o in outputs.items() }
            self.run_update_publisher.publish(run_id, {"outputs": msg})

        # Publish to output update subscribers.
        if run_id in self.output_update_publisher:
            for output_id, output in outputs.items():
                self.output_update_publisher.publish(run_id, output)


    def _transition(self, run, state, *, meta={}, **kw_args):
        """
        Transitions `run` to `state`, updating it with `kw_args`.

        :param meta:
          Metadata updates.  Sets or replaces run metadata keys from this
          mapping.
        """
        time = now()
        run_id = run.run_id

        # A run is no longer expected once it is no longer scheduled.
        if run.expected and state not in {State.new, State.scheduled}:
            self.__db.run_log_db.flush(run.run_id)
            run.expected = False

        # Transition the run object.
        run._transition(time, state, meta=meta, **kw_args)
        # Persist the new state.
        self.run_store.update(run, time)

        # Publish to run update subscribers.
        if run_id in self.run_update_publisher:
            msg = {"run": run_to_summary_jso(run)}
            if len(meta) > 0:
                msg["meta"] = run.meta
            self.run_update_publisher.publish(run_id, msg)
        # Publish to summary subscribers.
        self.summary_publisher.publish(messages.make_run_transition(run))
        # If the run is finished, close the output update publisher.
        if state.finished:
            self.output_update_publisher.close(run_id)

        self.__start_actions(run)


    def _validate_run(self, run):
        """
        :raise RuntimeError:
          `run` is invalid.
        """
        # The job ID must be valid.
        job = self.jobs.get_job(run.inst.job_id)

        # Args must match job params.
        args = frozenset(run.inst.args)
        missing, extra = job.params - args, args - job.params
        if missing:
            raise MissingArgumentError(run, *missing)
        if extra:
            raise ExtraArgumentError(run, *extra)

        return job


    # FIXME: Why is this here?
    def _propagate_args(self, old_args, inst):
        job = self.jobs.get_job(inst.job_id)
        args = runs.propagate_args(old_args, job, inst.args)
        return runs.Instance(inst.job_id, args)


    # --- API ------------------------------------------------------------------

    # FIXME: Move the API elsewhere.

    async def schedule(self, time, inst, *, expected=False):
        """
        Creates and schedules a new run.

        This is the only way to add a new run to the scheduler instance.

        :param time:
          The schedule time at which to run the run.  If `None`, the run
          is run now, instead of scheduled.
        :return:
          The run, either scheduled or error.
        """
        time = None if time is None else Time(time)

        # Create the run and add it to the run store, which assigns it a run ID
        # and persists it.
        run = Run(inst, expected=expected)
        self.run_store.add(run)

        # Check that the run is valid and get it ready.
        try:
            job = self.jobs.get_job(run.inst.job_id)
            validate_args(run, job.params)
            bind(run, job, self.jobs)
            # Attach job labels to the run.
            run.meta["job"] = {
                "labels": job.meta.get("labels", []),
            }
        except Exception as exc:
            self._run_exc(run, message=str(exc))
            return run

        if time is None:
            # Transition to scheduled and immediately to wait.
            self.run_log.record(run, "scheduled: now")
            self._transition(run, State.scheduled, times={"schedule": now()})
            self._wait(run)
        else:
            # Schedule for the future.
            self.run_log.record(run, f"scheduled: {time}")
            self._transition(run, State.scheduled, times={"schedule": time})
            await self.scheduled.schedule(time, run)

        return run


    async def skip(self, run):
        """
        Skips a scheduled or waiting run.

        Unschedules the run and sets it to the skipped state.
        """
        if run.state == State.scheduled:
            self.scheduled.unschedule(run)

        elif run.state == State.waiting:
            # Cancel the waiting task.
            await self.__wait_tasks.cancel(run.run_id)

        else:
            raise RunError(f"can't skip {run.run_id} in state {run.state.name}")

        self.run_log.info(run, "skipped")
        self._transition(run, State.skipped)


    async def start(self, run):
        """
        Immediately starts a scheduled or waiting run.
        """
        if run.state == State.scheduled:
            self.scheduled.unschedule(run)
            self.run_log.info(run, "scheduled run started by override")
            self._wait(run)

        elif run.state == State.waiting:
            # Cancel the waiting task.  It will remove itself when done.
            await self.__wait_tasks.cancel(run.run_id)
            self.run_log.info(run, "waiting run started by override")
            # Start the run.
            self._start(run)

        else:
            raise RunError(f"can't start {run.run_id} in state {run.state.name}")


    async def mark(self, run, state):
        """
        Transitions a run to a different finished `state`.

        :param run:
          Run, in a finished state.
        :param state:
          A different finished state.
        """
        if not state.finished:
            raise RunError(f"can't mark {run.run_id} to state {state.name}")
        elif not run.state.finished:
            raise RunError(f"can't mark {run.run_id} in state {run.state.name}")
        elif state == run.state:
            raise RunError(f"run {run.run_id} already in state {state.name}")
        else:
            self._transition(run, state, force=True)
            self.run_log.info(run, f"marked as {state.name}")


    def get_run_log(self, run_id):
        """
        Returns the run log for a run.
        """
        # Make sure the run ID is valid.
        self.run_store.get(run_id)
        return self.__db.run_log_db.query(run_id=run_id)


    async def rerun(self, run, *, time=None):
        """
        Creates a rerun of `run`.

        :param time:
          The time at which to schedule the rerun.  If `None`, runs the rerun
          immediately.
        """
        # Create the new run.
        log.info(f"rerun: {run.run_id} at {time or 'now'}")
        new_run = await self.schedule(time, run.inst)
        self.run_log.info(new_run, f"scheduled as rerun of {run.run_id}")
        return new_run


    async def send_signal(self, run, signal):
        """
        :raise RuntimeError:
          `run` is not running.
        """
        signal = to_signal(signal)
        if run.state != State.running:
            raise RuntimeError(f"invalid run state for signal: {run.state.name}")
        assert run.program is not None

        self.run_log.info(run, f"sending {signal.name}")
        try:
            await run.program.signal(run.run_id, run.run_state, signal)
        except Exception:
            self.run_log.exc(run, f"sending {signal.name} failed")
            raise RuntimeError(f"sending {signal.name} failed")


    async def shut_down(self):
        log.info("shutting down Apsis")
        await self.__action_tasks.cancel_all()
        await self.__wait_tasks.cancel_all()
        await self.__run_tasks.cancel_all()
        await self.__tasks.cancel_all()
        log.info("Apsis shut down")


    async def __check_async(self):
        """
        Monitors the async event loop.
        """
        while True:
            # Wake up on the next round 10 seconds.
            t = now()
            next_second = t.EPOCH + math.ceil((t - t.EPOCH + 0.01) / 10) * 10
            await asyncio.sleep(next_second - t)

            # See how late we are.
            latency = now() - next_second
            self.__check_async_stats = {
                "latency": latency,
            }


    def get_stats(self):
        res = resource.getrusage(resource.RUSAGE_SELF)
        stats = {
            "start_time"            : str(self.__start_time),
            "time"                  : str(now()),
            "async"                 : self.__check_async_stats,
            "rusage_maxrss"         : res.ru_maxrss * 1024,
            "rusage_utime"          : res.ru_utime,
            "rusage_stime"          : res.ru_stime,
            "tasks": {
                "num_waiting"       : len(self.__wait_tasks),
                "num_running"       : len(self.__run_tasks),
                "num_action"        : len(self.__action_tasks),
            },
            "len_runlogdb_cache"    : len(self.__db.run_log_db._RunLogDB__cache),
            "scheduled"             : self.scheduled.get_stats(),
            "run_store"             : self.run_store.get_stats(),
            "outputs"               : self.outputs.get_stats(),
            "summary_publisher"     : self.summary_publisher.get_stats(),
        }

        try:
            with open("/proc/self/statm") as file:
                statm = list(map(int, next(file).strip().split()))
        except FileNotFoundError:
            pass
        else:
            stats.update({
                "statm_size"        : statm[0] * PAGESIZE,
                "statm_resident"    : statm[1] * PAGESIZE,
            })

        return stats



#-------------------------------------------------------------------------------

async def _wait_loop(apsis, run, timeout):
    """
    The wait loop for a single run.
    """
    conds = list(run.conds)

    def wait_with_timeout(cond_wait):
        """
        :param cond_wait:
          The cond's wait coro.
        """
        if timeout is None:
            waiting_timeout = None
        else:
            # Adjust timeout to be relative to the time the run started waiting.
            try:
                waiting_time = run.times["waiting"]
            except KeyError:
                log.error(f"no waiting time in run: {run}")
                waiting_timeout = timeout
            else:
                # Subtract time we have already waited from the timeout.
                waiting_timeout = timeout - (now() - waiting_time)
        return asyncio.wait_for(cond_wait, waiting_timeout)


    if len(conds) > 0:
        apsis.run_log.record(run, f"waiting until: {conds[0]}")

    while len(conds) > 0:
        cond = conds[0]
        try:
            match cond:
                case PolledCondition():
                    result = await wait_with_timeout(cond.wait())

                # Special handling for nonmonotonic conditions involving
                # other runs.  After async waiting the condition, check
                # one more time synchronously before continuing
                # (synchronously) to transition.
                case NonmonotonicRunStoreCondition():
                    while True:
                        result = await wait_with_timeout(cond.wait(apsis.run_store))
                        # Last check, synchronously.
                        result = cond.check(apsis.run_store)
                        if result is not False:
                            break

                case RunStoreCondition():
                    result = await wait_with_timeout(cond.wait(apsis.run_store))

                case _:
                    assert False, f"not implemented: {cond!r}"

        except asyncio.CancelledError:
            raise

        except asyncio.TimeoutError:
            msg = f"waiting for {cond}: timeout after {timeout} s"
            apsis.run_log.info(run, msg)
            apsis._transition(run, State.error)
            return

        except Exception:
            msg = f"waiting for {cond}: failed"
            log.error(msg, exc_info=True)
            apsis._run_exc(run, message=msg)
            return

        match result:
            case True:
                # The condition is satisfied.  Proceed to the next.
                conds.pop(0)
                if len(conds) > 0:
                    apsis.run_log.record(run, f"waiting until: {conds[0]}")

            case cond.Transition(state):
                # Force a transition.
                apsis.run_log.info(run, result.reason or f"{state}: {cond}")
                apsis._transition(run, state)
                # Don't wait for further conds.
                return

            case _:
                assert False, f"invalid condition wait result: {result!r}"

    else:
        # Start the run.
        apsis._start(run)


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


async def _process_updates(apsis, run, updates):
    """
    Processes program `updates` for `run` until the program is finished.
    """
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


def _unschedule_runs(apsis, job_id):
    """
    Deletes all scheduled expected runs of `job_id`.
    """
    _, runs = apsis.run_store.query(job_id=job_id, state=State.scheduled)
    runs = [ r for r in runs if r.expected ]

    for run in runs:
        log.info(f"removing: {run.run_id}")
        apsis.scheduled.unschedule(run)
        apsis.run_store.remove(run.run_id)
        apsis.summary_publisher.publish(messages.make_run_delete(run))


async def reschedule_runs(apsis, job_id):
    """
    Reschedules runs of `job_id`.

    Unschedules and deletes existing scheduled runs.  Thenq rebuilds and
    reschedules runs according to the current job schedules.
    """
    scheduler = apsis.scheduler
    scheduled = apsis.scheduled

    # Get the time up to which scheduled runs were started.
    scheduled_time = scheduled.get_scheduled_time()
    # Get the time up to which jobs were scheduled.
    scheduler_time = scheduler.get_scheduler_time()

    # Unschedule all runs of this job.
    _unschedule_runs(apsis, job_id)

    # Restore scheduled runs, by rebuilding them between the scheduled time
    # and the scheduler time.
    job = apsis.jobs.get_job(job_id)
    schedule = list(get_insts_to_schedule(job, scheduled_time, scheduler_time))
    for time, inst in schedule:
        await apsis.schedule(time, inst, expected=True)


async def reload_jobs(apsis, *, dry_run=False):
    """
    :param dry_run:
      If true, determine changes but don't apply them.
    :return:
      Job IDs that have been removed, job IDs that have been added, and job IDs
      that have changed.
    """
    # FIXME: Refactor to avoid using private attributes and methods.
    jobs0       = apsis.jobs._Jobs__jobs_dir
    job_db      = apsis.jobs._Jobs__job_db

    # Reload the contents of the jobs dir.
    log.info(f"reloading jobs from {jobs0.path}")
    jobs1 = load_jobs_dir(jobs0.path)

    # Diff them.
    rem_ids, add_ids, chg_ids = diff_jobs_dirs(jobs0, jobs1)

    if not dry_run:
        for job_id in rem_ids:
            log.info(f"unscheduling removed job: {job_id}")
            _unschedule_runs(apsis, job_id)
        for job_id in chg_ids:
            log.info(f"unscheduling changed job: {job_id}")
            _unschedule_runs(apsis, job_id)

        # Use the new jobs, including for scheduling.
        apsis.jobs = Jobs(jobs1, job_db)
        apsis.scheduler.set_jobs(apsis.jobs)

        # Reschedule runs.
        for job_id in add_ids:
            log.info(f"scheduling added job: {job_id}")
            await reschedule_runs(apsis, job_id)
        for job_id in sorted(chg_ids):
            log.info(f"scheduling changed: {job_id}")
            await reschedule_runs(apsis, job_id)

        # Publish job changes.
        publish = apsis.summary_publisher.publish
        for job_id in rem_ids:
            publish(messages.make_job_delete(job_id))
        for job_id in add_ids:
            publish(messages.make_job_add(apsis.jobs.get_job(job_id)))
        for job_id in chg_ids:
            publish(messages.make_job(apsis.jobs.get_job(job_id)))

    return rem_ids, add_ids, chg_ids


async def _retire_loop(apsis):
    """
    Periodically retires runs older than `runs.lookback`.
    """
    log.info("starting retire loop")
    runs_cfg = apsis.cfg.get("runs", {})
    retire_lookback = runs_cfg.get("lookback", None)
    if retire_lookback is None:
        log.info("no runs.lookback in config; no retire loop")
        return

    while True:
        try:
            min_timestamp = now() - retire_lookback
            apsis.run_store.retire_old(min_timestamp)
        except Exception:
            log.error("retire failed", exc_info=True)
            return

        await asyncio.sleep(60)


