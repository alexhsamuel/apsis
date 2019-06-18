import asyncio
import logging
from   ora import now, Time
import sys
import traceback

from   . import actions
from   .exc import ConditionError
from   .history import RunHistory
from   .jobs import Jobs
from   .lib.asyn import cancel_task
from   .program import ProgramError, ProgramFailure, Output, OutputMetadata
from   . import runs
from   .runs import Run, Runs, MissingArgumentError, ExtraArgumentError
from   .runs import get_bind_args
from   .scheduled import ScheduledRuns
from   .scheduler import Scheduler
from   .waiter import Waiter

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
        self.__db = db
        self.run_history = RunHistory(self.__db.run_history_db)
        self.jobs = Jobs(jobs, db.job_db)

        try:
            runs_lookback = cfg["runs_lookback"]
        except KeyError:
            min_timestamp = None
        else:
            min_timestamp = now() - runs_lookback
        self.runs = Runs(db, min_timestamp=min_timestamp)

        log.info("scheduling runs")
        self.scheduled = ScheduledRuns(db.clock_db, self.__wait)
        self.__waiter = Waiter(self.runs, self.__start, self.run_history)
        # For now, expose the output database directly.
        self.outputs = db.output_db
        # Tasks for running jobs currently awaited.
        self.__running_tasks = {}

        # Actions applied to all runs.
        self.__actions = [ actions.action_from_jso(o) for o in cfg["actions"] ]

        # Continue scheduling from the last time we handled scheduled jobs.
        # FIXME: Rename: schedule horizon?
        stop_time = db.clock_db.get_time()
        log.info(f"scheduling runs from {stop_time}")
        self.scheduler = Scheduler(self.jobs, self.schedule, stop_time)


    async def restore(self):
        """
        Restores scheduled, waiting, and running runs from DB.
        """
        async def reschedule(run, time):
            # Bind job attributes to the run.
            if run.program is None:
                run.program = self.__get_program(run)
            if run.conds is None:
                try:
                    run.conds = list(self.__get_conds(run))
                except Exception:
                    self._run_exc(run, message="invalid condition")
                    return

            if time is None:
                self.run_history.info(run, f"restored: waiting")
                await self.__waiter.start(run)
            else:
                self.run_history.info(run, f"restored: scheduled for {time}")
                await self.scheduled.schedule(time, run)

        # Restore scheduled runs from DB.
        log.info("restoring scheduled runs")
        _, scheduled_runs = self.runs.query(state=Run.STATE.scheduled)
        for run in scheduled_runs:
            assert not run.expected
            await reschedule(run, run.times["schedule"])

        # Restore waiting runs from DB.
        log.info("restoring waiting runs")
        _, waiting_runs = self.runs.query(state=Run.STATE.waiting)
        for run in waiting_runs:
            assert not run.expected
            await reschedule(run, None)

        # Reconnect to running runs.
        _, running_runs = self.runs.query(state=Run.STATE.running)
        log.info(f"reconnecting running runs")
        for run in running_runs:
            assert run.program is not None
            self.run_history.record(
                run, f"at startup, reconnecting to running {run.run_id}")
            future = run.program.reconnect(run.run_id, run.run_state)
            self.__finish(run, future)


    def start_loops(self):
        # Set up the scheduler.
        log.info("starting scheduler loop")
        self.__scheduler_task = asyncio.ensure_future(self.scheduler.loop())

        # Set up the manager for scheduled tasks.
        log.info("starting scheduled loop")
        self.__scheduled_task = asyncio.ensure_future(self.scheduled.loop())

        # Set up the waiter for waiting tasks.
        log.info("scheduling waiter loop")
        self.__waiter_task = asyncio.ensure_future(self.__waiter.loop())


    def __get_conds(self, run):
        """
        Constructs conditions for a run, with arguments bound.
        """
        job = self.jobs.get_job(run.inst.job_id)
        for cond in job.conds:
            try:
                yield cond.bind(run, self.jobs)
            except Exception:
                raise ConditionError(str(cond))


    async def __wait(self, run):
        """
        Waits `run`, if it has pending conditions, otherwise starts it.
        """
        log.info(f"waiting: {run}")
        self._transition(run, run.STATE.waiting)
        await self.__waiter.start(run)


    def __get_program(self, run):
        """
        Constructs the program for a run, with arguments bound.
        """
        job = self.jobs.get_job(run.inst.job_id)
        return job.program.bind(get_bind_args(run))


    async def __start(self, run):
        try:
            running, coro = await run.program.start(run)

        except ProgramError as exc:
            # Program failed to start.
            self.run_history.exc(run, "program start")
            self._transition(
                run, run.STATE.error, 
                meta    =exc.meta,
                times   =exc.times,
                outputs =exc.outputs,
            )

        else:
            # Program started successfully.
            self.run_history.info(run, "program started")
            self._transition(run, run.STATE.running, **running.__dict__)
            future = asyncio.ensure_future(coro)
            self.__finish(run, future)


    def __finish(self, run, future):
        def done(future):
            try:
                try:
                    success = future.result()
                except asyncio.CancelledError:
                    log.info(
                        f"canceled waiting for run to complete: {run.run_id}")
                    return

            except ProgramFailure as exc:
                # Program ran and failed.
                self.run_history.record(run, f"program failure: {exc.message}")
                self._transition(
                    run, run.STATE.failure, 
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            except ProgramError as exc:
                # Program failed to start.
                self.run_history.record(run, f"program error: {exc.message}")
                self._transition(
                    run, run.STATE.error, 
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            else:
                # Program ran and completed successfully.
                self.run_history.record(run, f"program success")
                self._transition(
                    run, run.STATE.success,
                    meta    =success.meta,
                    times   =success.times,
                    outputs =success.outputs,
                )

            del self.__running_tasks[run.run_id]

        self.__running_tasks[run.run_id] = future
        future.add_done_callback(done)


    def __rerun(self, run):
        """
        Reruns a failed run, if indicated by the job's rerun policy.
        """
        job = self.jobs.get_job(run.inst.job_id)
        if job.reruns.count == 0:
            # No reruns.
            return
        
        # Collect all reruns of this run, including the original run.
        _, runs = self.runs.query(rerun=run.rerun)
        runs = list(runs)

        if len(runs) > job.reruns.count:
            # No further reruns.
            log.info(f"retry max count exceeded: {run.rerun}")
            return

        time = now()

        main_run, = ( r for r in runs if r.run_id == run.rerun )
        if (main_run.times["schedule"] is not None
            and time - main_run.times["schedule"] > job.reruns.max_delay):
            # Too much time has elapsed.
            log.info(f"retry max delay exceeded: {run.rerun}")

        # OK, we can rerun.
        rerun_time = time + job.reruns.delay
        asyncio.ensure_future(self.rerun(run, time=rerun_time))


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
            self.run_history.error(run, exc)
        else:
            actions.extend(job.actions)

        loop = asyncio.get_event_loop()

        async def wrap(run, action):
            try:
                await action(self, run)
            except Exception:
                self.run_history.exc(run, "action")

        for action in actions + self.__actions:
            # FIXME: Hold the future?  Or make sure it doesn't run for long?
            loop.create_task(wrap(run, action))


    # --- Internal API ---------------------------------------------------------

    def _run_exc(self, run, *, message=None):
        """
        Transitions `run` to error, with the current exception attached.
        """
        self.run_history.exc(run, message)

        outputs = {}
        if sys.exc_info()[0] is not None:
            # Attach the exception traceback as run output.
            tb = traceback.format_exc().encode()
            # FIXME: For now, use the name "output" as this is the only one 
            # the UIs render.  In the future, change to "traceback".
            outputs["output"] = Output(
                OutputMetadata("output", len(tb), content_type="text/plain"),
                tb
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
            self.__db.run_history_db.flush(run.run_id)
            run.expected = False

        # Transition the run object.
        run._transition(time, state, **kw_args)

        # Persist outputs.
        # FIXME: We are persisting runs assuming all are new.  This is only
        # OK for the time being because outputs are always added on the final
        # transition.  In general, we have to persist new outputs only.
        for output_id, output in outputs.items():
            self.__db.output_db.add(run.run_id, output_id, output)

        # Persist the new state.  
        self.runs.update(run, time)

        if state == run.STATE.failure:
            self.__rerun(run)

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


    def _propagate_args(self, old_args, inst):
        job = self.jobs.get_job(inst.job_id)
        args = runs.propagate_args(old_args, job, inst.args)
        return runs.Instance(inst.job_id, args)


    # --- API ------------------------------------------------------------------

    async def schedule(self, time, run):
        """
        Adds and schedules a new run.

        This is the only way to add a new run to the scheduler instance.

        :param time:
          The schedule time at which to run the run.  If `None`, the run
          is run now, instead of scheduled.
        :return:
          The scheduled run.
        """
        self.runs.add(run)

        time = None if time is None else Time(time)
        times = {} if time is None else {"schedule": time}

        try:
            self._validate_run(run)
        except RuntimeError:
            self._run_exc(run, message="invalid run")
            return run

        # Bind job attributes to the run.
        if run.program is None:
            run.program = self.__get_program(run)
        if run.conds is None:
            try:
                run.conds = list(self.__get_conds(run))
            except Exception:
                self._run_exc(run, message="invalid condition")
                return run

        if time is None:
            self.run_history.info(run, "scheduling for immediate run")
            await self.__wait(run)
            return run
        else:
            self.run_history.info(run, f"scheduling for {time}")
            self._transition(run, run.STATE.scheduled, times=times)
            await self.scheduled.schedule(time, run)
            return run


    async def cancel(self, run):
        """
        Cancels a scheduled run.

        Unschedules the run and sets it to the error state.
        """
        self.scheduled.unschedule(run)
        self.run_history.info(run, "cancelled")
        self._transition(run, run.STATE.error, message="cancelled")


    async def start(self, run):
        """
        Starts immediately a scheduled run.
        """
        # FIXME: Race conditions?
        self.scheduled.unschedule(run)
        await self.__wait(run)


    async def get_run_history(self, run_id):
        """
        Returns history log for a run.
        """
        # Make sure the run ID is valid.
        self.runs.get(run_id)
        return self.__db.run_history_db.query(run_id=run_id)


    async def rerun(self, run, *, time=None):
        """
        Creates a rerun of `run`.

        :param time:
          The time at which to schedule the rerun.  If `None`, runs the rerun
          immediately.
        """
        # Create the new run.
        log.info(f"rerun: {run.run_id} at {time or 'now'}")
        rerun = run.run_id if run.rerun is None else run.rerun
        new_run = Run(run.inst, rerun=rerun)
        await self.schedule(time, new_run)
        return new_run


    async def shut_down(self):
        log.info("shutting down Apsis")
        await cancel_task(self.__scheduler_task, "scheduler", log)
        await cancel_task(self.__scheduled_task, "scheduled", log)
        await cancel_task(self.__waiter_task, "waiter", log)
        for run_id, task in self.__running_tasks.items():
            await cancel_task(task, f"run {run_id}", log)
        await self.runs.shut_down()
        log.info("Apsis shut down")
        


