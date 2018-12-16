import asyncio
import logging
from   ora import now, Time

from   .jobs import Jobs
from   .lib.async import cancel_task
from   .program import ProgramError, ProgramFailure
from   .runs import Run, Runs, MissingArgumentError, ExtraArgumentError
from   .scheduled import ScheduledRuns
from   .scheduler import Scheduler

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

    def __init__(self, jobs, db):
        log.info("creating Apsis instance")
        self.__db = db
        self.jobs = Jobs(jobs, db.job_db)
        self.runs = Runs(db.run_db)
        log.info("scheduling runs")
        self.scheduled = ScheduledRuns(db.clock_db, self.__start)
        # For now, expose the output database directly.
        self.outputs = db.output_db
        # Tasks for running jobs currently awaited.
        self.__running_tasks = {}

        # Restore scheduled runs from DB.
        log.info("restoring scheduled runs")
        _, scheduled_runs = self.runs.query(state=Run.STATE.scheduled)
        for run in scheduled_runs:
            if run.expected:
                # Expected, scheduled runs should not have been persisted.
                log.error(
                    f"not rescheduling expected, scheduled run {run.run_id}")
            else:
                sched_time = run.times["schedule"]
                self._log_run_history(
                    run.run_id, 
                    f"at startup, rescheduled {run.run_id} for {sched_time}"
                )
                self.scheduled.schedule(sched_time, run)

        # Continue scheduling from the last time we handled scheduled jobs.
        # FIXME: Rename: schedule horizon?
        stop_time = db.clock_db.get_time()
        log.info(f"scheduling runs from {stop_time}")
        self.scheduler = Scheduler(self.jobs, self.schedule, stop_time)

        # Set up the scheduler.
        log.info("starting scheduler loop")
        self.__scheduler_task = asyncio.ensure_future(self.scheduler.loop())

        # Set up the manager for scheduled tasks.
        log.info("starting scheduled loop")
        self.__scheduled_task = asyncio.ensure_future(self.scheduled.loop())

        # Reconnect to running runs.
        _, running_runs = self.runs.query(state=Run.STATE.running)
        log.info(f"reconnecting running runs")
        for run in running_runs:
            assert run.program is not None
            self._log_run_history(
                run.run_id,
                f"at startup, reconnecting to running {run.run_id}"
            )
            future = run.program.reconnect(run.run_id, run.run_state)
            self.__wait(run, future)

        log.info("Apsis instance ready")


    def __get_program(self, run):
        """
        Constructs the program for a run, with arguments bound.
        """
        job = self.jobs.get_job(run.inst.job_id)
        program = job.program.bind({
            "run_id": run.run_id,
            "job_id": run.inst.job_id,
            **run.inst.args,
        })
        return program


    async def __start(self, run):
        if run.program is None:
            run.program = self.__get_program(run)

        try:
            running, coro = await run.program.start(run)

        except ProgramError as exc:
            # Program failed to start.
            self._log_run_history(
                run.run_id,
                f"program start error: {exc.message}",
            )
            self._transition(
                run, run.STATE.error, 
                meta    =exc.meta,
                times   =exc.times,
                outputs =exc.outputs,
            )

        else:
            # Program started successfully.
            self._log_run_history(
                run.run_id,
                "program started",
            )
            self._transition(run, run.STATE.running, **running.__dict__)
            future = asyncio.ensure_future(coro)
            self.__wait(run, future)


    def __wait(self, run, future):
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
                self._log_run_history(
                    run.run_id,
                    f"program failure: {exc.message}",
                )
                self._transition(
                    run, run.STATE.failure, 
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            except ProgramError as exc:
                # Program failed to start.
                self._log_run_history(
                    run.run_id,
                    f"program error: {exc.message}",
                )
                self._transition(
                    run, run.STATE.error, 
                    meta    =exc.meta,
                    times   =exc.times,
                    outputs =exc.outputs,
                )

            else:
                # Program ran and completed successfully.
                self._log_run_history(
                    run.run_id,
                    f"program success",
                )
                self._transition(
                    run, run.STATE.success,
                    meta    =success.meta,
                    times   =success.times,
                    outputs =success.outputs,
                )

            del self.__running_tasks[run.run_id]

        self.__running_tasks[run.run_id] = future
        future.add_done_callback(done)
        # FIXME: Don't just drop the future?


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


    # --- Internal API ---------------------------------------------------------

    def _log_run_history(self, run_id, message, *, timestamp=None):
        """
        Adds a timestamped history record to the history for `run_id`.

        :param timestamp:
          The time of the event; current time if none.
        """
        timestamp = now() if timestamp is None else timestamp
        self.__db.run_history_db.insert(run_id, timestamp, message)


    def _transition(self, run, state, *, outputs={}, **kw_args):
        """
        Transitions `run` to `state`, updating it with `kw_args`.
        """
        time = now()

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


    # --- API ------------------------------------------------------------------

    async def schedule(self, time, run):
        """
        Adds and schedules a new run.

        :param time:
          The schedule time at which to run the run.  If `None`, the run
          is run now, instead of scheduled.
        """
        self.runs.add(run)

        time = None if time is None else Time(time)
        times = {} if time is None else {"schedule": time}

        try:
            self._validate_run(run)
        except RuntimeError as exc:
            log.error("invalid run", exc_info=True)
            times["error"] = now()
            self._log_run_history(
                run.run_id, 
                f"invalid run: {exc}",
            )
            self._transition(
                run, run.STATE.error,
                times   =times,
            )
            return

        if time is None:
            self._log_run_history(run.run_id, "starting now")
            await self.__start(run)
        else:
            self.scheduled.schedule(time, run)
            self._log_run_history(run.run_id, f"scheduling for {time}")
            self._transition(run, run.STATE.scheduled, times=times)


    async def cancel(self, run):
        """
        Cancels a scheduled run.

        Unschedules the run and sets it to the error state.
        """
        self.scheduled.unschedule(run)
        self._log_run_history(run.run_id, "cancelled")
        self._transition(run, run.STATE.error, message="cancelled")


    async def start(self, run):
        """
        Starts immediately a scheduled run.
        """
        # FIXME: Race conditions?
        self.scheduled.unschedule(run)
        await self.__start(run)


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
        for run_id, task in self.__running_tasks.items():
            await cancel_task(task, f"run {run_id}", log)
        await self.runs.shut_down()
        log.info("Apsis shut down")
        


