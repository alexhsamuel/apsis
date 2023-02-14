import asyncio
import json
import logging
from   ora import now, Time
import resource
import sys
import traceback

from   .actions import Action
from   .exc import TimeoutWaiting
from   .host_group import config_host_groups
from   .jobs import Jobs, load_jobs_dir, diff_jobs_dirs
from   .lib.asyn import cancel_task
from   .program import ProgramError, ProgramFailure, Output, OutputMetadata
from   . import runs
from   .run_log import RunLog
from   .runs import Run, RunStore, RunError, MissingArgumentError, ExtraArgumentError
from   .runs import get_bind_args
from   .scheduled import ScheduledRuns
from   .scheduler import Scheduler, get_runs_to_schedule

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
        log.debug("creating Apsis instance")
        self.cfg = cfg
        # FIXME: This should go in `apsis.config.config_globals` or similar.
        config_host_groups(cfg)
        self.__db = db

        self.run_log = RunLog(self.__db.run_log_db)
        self.jobs = Jobs(jobs, db.job_db)

        # Actions applied to all runs.
        self.__actions = [ Action.from_jso(o) for o in cfg["actions"] ]

        try:
            runs_lookback = cfg["runs_lookback"]
        except KeyError:
            min_timestamp = None
        else:
            min_timestamp = now() - runs_lookback
        self.run_store = RunStore(db, min_timestamp=min_timestamp)

        log.info("scheduling runs")
        self.scheduled = ScheduledRuns(db.clock_db, self.__wait)
        self.__wait_tasks = {}
        self.__starting_tasks = {}
        # For now, expose the output database directly.
        self.outputs = db.output_db
        # Tasks for running jobs currently awaited.
        self.__running_tasks = {}

        # Continue scheduling from the last time we handled scheduled jobs.
        # FIXME: Rename: schedule horizon?
        stop_time = db.clock_db.get_time()
        log.info(f"scheduling runs from {stop_time}")

        self.scheduler = Scheduler(cfg, self.jobs, self.schedule, stop_time)

        self.__stats_loop = asyncio.ensure_future(self.stats_loop())


    async def restore(self):
        """
        Restores scheduled, waiting, and running runs from DB.
        """
        try:
            log.info("restoring")

            # Restore scheduled runs from DB.
            log.info("restoring scheduled runs")
            _, scheduled_runs = self.run_store.query(state=Run.STATE.scheduled)
            for run in scheduled_runs:
                assert not run.expected
                if not self.__prepare_run(run):
                    continue
                time = run.times["schedule"]
                self.run_log.info(run, f"restored: scheduled for {time}")
                await self.scheduled.schedule(time, run)

            # Restore waiting runs from DB.
            log.info("restoring waiting runs")
            _, waiting_runs = self.run_store.query(state=Run.STATE.waiting)
            for run in waiting_runs:
                assert not run.expected
                if not self.__prepare_run(run):
                    continue
                self.run_log.info(run, "restoring: waiting")
                self.__wait(run)

            # If a run is starting in the DB, we can't know if it actually
            # started or not, so mark it as error.
            log.info("processing starting runs")
            _, starting_runs = self.run_store.query(state=Run.STATE.starting)
            for run in starting_runs:
                self._transition(
                    run, run.STATE.error,
                    message="startup: starting; may or may not have started"
                )

            # Reconnect to running runs.
            _, running_runs = self.run_store.query(state=Run.STATE.running)
            log.info("reconnecting running runs")
            for run in running_runs:
                assert run.program is not None
                self.run_log.record(run, "restoring: reconnecting to running run")
                future = run.program.reconnect(run.run_id, run.run_state)
                self.__finish(run, future)

            log.info("restoring done")

        except Exception:
            log.critical("restore failed", exc_info=True)
            raise SystemExit(1)


    def start_loops(self):
        # Set up the scheduler.
        log.info("starting scheduler loop")
        self.__scheduler_task = asyncio.ensure_future(self.scheduler.loop())

        # Set up the manager for scheduled tasks.
        log.info("starting scheduled loop")
        self.__scheduled_task = asyncio.ensure_future(self.scheduled.loop())

        async def tracemalloc_loop():
            import tracemalloc
            try:
                tracemalloc.start()
                while True:
                    name = f"snapshot-{now():%~C@UTC}"
                    snapshot = tracemalloc.take_snapshot()
                    log.info(f"dumping: {name}")
                    snapshot.dump(name)
                    await asyncio.sleep(60)
            except:
                log.error("tracemalloc snapshot failed", exc_info=True)

        log.info("starting tracemalloc loop")
        self.__tracemalloc_task = asyncio.ensure_future(tracemalloc_loop())


    def __wait(self, run):
        """
        Starts waiting for `run`.
        """
        # Make sure the run is waiting.
        if run.state != run.STATE.waiting:
            self._transition(run, run.STATE.waiting)

        # If a max waiting time is configured, compute the timeout for this run.
        cfg = self.cfg.get("waiting", {})
        max_time = cfg.get("max_time", None)
        if max_time is None:
            timeout = None
        else:
            try:
                start = Time(run.times["waiting"])
            except KeyError:
                log.error(f"waiting run missing waiting time: {run.run_id}")
                # Fall back to current time.
                start = now()
            timeout = start + max_time

        async def loop():
            """
            The wait loop for a single run.
            """
            try:
                conds = list(run.conds)

                if len(conds) > 0:
                    self.run_log.info(run, f"waiting for condition: {conds[0]}")
                while len(conds) > 0:
                    cond = conds[0]

                    # FIXME: In the future, we won't poll run conditions, but
                    # rather check only on run transitions.
                    result = cond.check_runs(run, self.run_store)
                    if result is True:
                        result = await cond.check()

                    if isinstance(result, cond.Transition):
                        # Force a transition.
                        self.run_log.info(
                            run, result.reason or f"{cond} → {result.state}")
                        self._transition(run, result.state)
                        return

                    elif result is True:
                        self.run_log.info(run, f"satisfied {cond}")
                        conds.pop(0)
                        if len(conds) > 0:
                            self.run_log.info(
                                run, f"waiting for condition: {conds[0]}")

                    elif result is False:
                        # First cond is still blocking.
                        if timeout is not None:
                            # Check for timeout while waiting.
                            remaining = timeout - now()
                            if 0 < remaining:
                                sleep_time = min(cond.poll_interval, remaining)
                            else:
                                raise TimeoutWaiting(
                                    f"time out waiting after {max_time} sec")
                        else:
                            sleep_time = cond.poll_interval

                        await asyncio.sleep(sleep_time)

                    else:
                        assert False, f"invalid condition result: {result!r}"

                else:
                    # Start the run.
                    self.__start(run)

            except asyncio.CancelledError:
                raise
            except Exception:
                msg = f"waiting for {run.conds[0]} failed"
                log.error(msg, exc_info=True)
                self._run_exc(run, message=msg)

        task = asyncio.ensure_future(loop())
        self.__wait_tasks[run] = task
        task.add_done_callback(lambda _: self.__wait_tasks.pop(run))


    def __start(self, run):
        self.run_log.info(run, "program starting")
        self._transition(run, run.STATE.starting)

        async def start():
            try:
                running, coro = await run.program.start(run.run_id, self.cfg)

            except ProgramError as exc:
                # Program failed to start.
                self.run_log.exc(run, "program start")
                self._transition(
                    run, run.STATE.error,
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            else:
                # Program started successfully.
                self.run_log.info(run, "program started")
                self._transition(run, run.STATE.running, **running.__dict__)
                future = asyncio.ensure_future(coro)
                self.__finish(run, future)

        task = asyncio.ensure_future(start())
        self.__starting_tasks[run] = task
        task.add_done_callback(lambda _: self.__starting_tasks.pop(run))


    def __finish(self, run, future):
        def done(future):
            try:
                try:
                    success = future.result()
                except asyncio.CancelledError:
                    log.info(
                        f"cancelled waiting for run to complete: {run.run_id}")
                    return

            except ProgramFailure as exc:
                # Program ran and failed.
                self.run_log.record(run, f"program failure: {exc.message}")
                self._transition(
                    run, run.STATE.failure,
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            except ProgramError as exc:
                # Program failed to start.
                self.run_log.record(run, f"program error: {exc.message}")
                self._transition(
                    run, run.STATE.error,
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            except Exception as exc:
                # Program raised some other exception.
                log.error(
                    f"exception waiting for run: {run.run_id}", exc_info=True)
                self.run_log.record(
                    run, f"internal error in program: {exc}")
                tb = traceback.format_exc().encode()
                self._transition(
                    run, run.STATE.error,
                    outputs ={
                        "output": Output(
                            OutputMetadata("traceback", length=len(tb)),
                            tb
                        ),
                    }
                )

            else:
                # Program ran and completed successfully.
                self.run_log.record(run, "program success")
                self._transition(
                    run, run.STATE.success,
                    meta    =success.meta,
                    times   =success.times,
                    outputs =success.outputs,
                )

            del self.__running_tasks[run.run_id]

        self.__running_tasks[run.run_id] = future
        future.add_done_callback(done)


    def __prepare_run(self, run):
        """
        Prepares a run for schedule or restore, using its job.

        The run must already be in the run DB.

        On failure, transitions the run to error and returns false.
        """
        try:
            job = self._validate_run(run)
        except Exception as exc:
            self._run_exc(run, message=str(exc))
            return False

        if run.program is None:
            try:
                run.program = job.program.bind(get_bind_args(run))
            except Exception as exc:
                self._run_exc(run, message=f"invalid program: {exc}")
                return False

        if run.conds is None:
            try:
                run.conds = [ c.bind(run, self.jobs) for c in job.conds ]
            except Exception as exc:
                self._run_exc(run, message=f"invalid condition: {exc}")
                return False

        # Attach job labels to the run.
        if run.meta.get("labels") is None:
            run.meta["labels"] = job.meta.get("labels", [])

        return True


    def __do_actions(self, run):
        """
        Performs configured actions on `run`.
        """
        actions = []

        # Find actions attached to the job.
        job_id = run.inst.job_id
        try:
            job = self.jobs.get_job(job_id)
        except LookupError as exc:
            # Job is gone; can't get the actions.
            self.run_log.error(run, exc)
        else:
            actions.extend(job.actions)

        loop = asyncio.get_event_loop()

        async def wrap(run, action):
            try:
                await action(self, run)
            except Exception:
                self.run_log.exc(run, "action")

        for action in actions + self.__actions:
            # FIXME: Hold the future?  Or make sure it doesn't run for long?
            loop.create_task(wrap(run, action))


    # --- Internal API ---------------------------------------------------------

    def _run_exc(self, run, *, message=None):
        """
        Transitions `run` to error, with the current exception attached.
        """
        self.run_log.exc(run, message)

        outputs = {}
        exc_type, exc, _ = sys.exc_info()
        if exc_type is not None:
            # Attach the exception traceback as run output.
            if issubclass(exc_type, RuntimeError):
                msg = str(exc).encode()
            else:
                msg = traceback.format_exc().encode()
            # FIXME: For now, use the name "output" as this is the only one
            # the UIs render.  In the future, change to "traceback".
            outputs["output"] = Output(
                OutputMetadata("output", len(msg), content_type="text/plain"),
                msg
            )

        self._transition(
            run, run.STATE.error,
            times={"error": now()},
            message=message,
            outputs=outputs,
        )


    def _transition(self, run, state, *, outputs={}, **kw_args):
        """
        Transitions `run` to `state`, updating it with `kw_args`.
        """
        time = now()

        # A run is no longer expected once it is no longer scheduled.
        if run.expected and state not in {
                run.STATE.new,
                run.STATE.scheduled,
        }:
            self.__db.run_log_db.flush(run.run_id)
            run.expected = False

        # Transition the run object.
        run._transition(time, state, **kw_args)

        # Persist outputs.
        # FIXME: We are persisting outputs assuming all are new.  This is only
        # OK for the time being because outputs are always added on the final
        # transition.  In general, we have to persist new outputs only.
        for output_id, output in outputs.items():
            self.__db.output_db.add(run.run_id, output_id, output)

        # Persist the new state.
        self.run_store.update(run, time)

        self.__do_actions(run)


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


    def _propagate_args(self, old_args, inst):
        job = self.jobs.get_job(inst.job_id)
        args = runs.propagate_args(old_args, job, inst.args)
        return runs.Instance(inst.job_id, args)


    # --- API ------------------------------------------------------------------

    # FIXME: Move the API elsewhere.

    async def schedule(self, time, run):
        """
        Adds and schedules a new run.

        This is the only way to add a new run to the scheduler instance.

        :param time:
          The schedule time at which to run the run.  If `None`, the run
          is run now, instead of scheduled.
        :return:
          The run, either scheduled or error.
        """
        time = None if time is None else Time(time)

        self.run_store.add(run)
        if not self.__prepare_run(run):
            return run

        if time is None:
            self.run_log.info(run, "scheduling for immediate run")
            self._transition(run, run.STATE.scheduled, times={"schedule": now()})
            self.__wait(run)
            return run
        else:
            self.run_log.info(run, f"scheduling for {time}")
            self._transition(run, run.STATE.scheduled, times={"schedule": time})
            await self.scheduled.schedule(time, run)
            return run


    async def skip(self, run):
        """
        Skips a scheduled or waiting run.

        Unschedules the run and sets it to the skipped state.
        """
        if run.state == run.STATE.scheduled:
            self.scheduled.unschedule(run)
        elif run.state == run.STATE.waiting:
            await cancel_task(self.__wait_tasks.pop(run), f"waiting for {run}", log)
        else:
            raise RunError(f"can't skip {run.run_id} in state {run.state.name}")
        self.run_log.info(run, "skipped")
        self._transition(run, run.STATE.skipped, message="skipped")


    async def start(self, run):
        """
        Starts immediately a scheduled or waiting run.
        """
        # FIXME: Race conditions?
        if run.state == run.STATE.scheduled:
            self.scheduled.unschedule(run)
            self.run_log.info(run, "scheduled run started by override")
            self.__wait(run)
        elif run.state == run.STATE.waiting:
            self.__wait_tasks.pop(run).cancel()
            self.run_log.info(run, "waiting run started by override")
            self.__start(run)
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
        if state not in Run.FINISHED:
            raise RunError(f"can't mark {run.run_id} to state {state.name}")
        elif run.state not in Run.FINISHED:
            # FIXME: Add a 'force' option to allow this?
            raise RunError(f"can't mark {run.run_id} in state {run.state.name}")
        elif state == run.state:
            raise RunError(f"run {run.run_id} already in state {state.name}")
        else:
            self._transition(run, state, force=True)
            self.run_log.info(run, f"marked as {state.name}")


    async def get_run_log(self, run_id):
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
        timestamp = now()
        new_run = Run(run.inst)
        await self.schedule(time, new_run)
        self.run_log.info(
            new_run, f"scheduled as rerun of {run.run_id}", timestamp=timestamp)
        return new_run


    async def shut_down(self):
        log.info("shutting down Apsis")
        await cancel_task(self.__scheduler_task, "scheduler", log)
        await cancel_task(self.__scheduled_task, "scheduled", log)
        await cancel_task(self.__tracemalloc_task, "tracemalloc", log)
        for run, task in list(self.__wait_tasks.items()):
            await cancel_task(task, f"waiting for {run}", log)
        for run, task in list(self.__starting_tasks.items()):
            await cancel_task(task, f"starting {run}", log)
        for run_id, task in self.__running_tasks.items():
            await cancel_task(task, f"run {run_id}", log)
        await self.run_store.shut_down()
        log.info("Apsis shut down")


    def get_stats(self):
        res = resource.getrusage(resource.RUSAGE_SELF)
        stats = {
            "rusage_maxrss"         : res.ru_maxrss * 1024,
            "rusage_utime"          : res.ru_utime,
            "rusage_stime"          : res.ru_stime,
            "num_waiting_tasks"     : len(self.__wait_tasks),
            "num_starting_tasks"    : len(self.__starting_tasks),
            "num_running_tasks"     : len(self.__running_tasks),
            "num_runstore_runs"     : len(self.run_store._RunStore__runs),
            "len_runlogdb_cache"    : len(self.__db.run_log_db._RunLogDB__cache),
            "len_scheduled_heap"    : len(self.scheduled._ScheduledRuns__heap),
            "num_scheduled_entries" : len(self.scheduled._ScheduledRuns__scheduled),
        }

        try:
            statm = list(map(int, next(open("/proc/self/statm")).strip().split()))
        except FileNotFoundError:
            pass
        else:
            stats.update({
                "statm_size"        : statm[0],
                "statm_resident"    : statm[1],
            })

        return stats


    async def stats_loop(self):
        log.warning("starting stats_loop")
        while True:
            try:
                stats = self.get_stats()
            except Exception:
                log.error("stats failed", exc_info=True)
            else:
                log.info("stats: " + json.dumps(stats))
            await asyncio.sleep(60)



#-------------------------------------------------------------------------------

def _unschedule_runs(apsis, job_id):
    """
    Deletes all scheduled expected runs of `job_id`.
    """
    _, runs = apsis.run_store.query(job_id=job_id, state=Run.STATE.scheduled)
    runs = [ r for r in runs if r.expected ]

    for run in runs:
        log.info(f"removing: {run.run_id}")
        apsis.scheduled.unschedule(run)
        apsis.run_store.remove(run.run_id)


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
    schedule = list(get_runs_to_schedule(job, scheduled_time, scheduler_time))
    for time, run in schedule:
        await apsis.schedule(time, run)


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

        for job_id in add_ids:
            log.info(f"scheduling added job: {job_id}")
            await reschedule_runs(apsis, job_id)
        for job_id in sorted(chg_ids):
            log.info(f"scheduling changed: {job_id}")
            await reschedule_runs(apsis, job_id)

    return rem_ids, add_ids, chg_ids


