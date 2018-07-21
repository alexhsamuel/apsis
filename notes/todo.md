# Current

- search, filtering in RunsList
- search, filtering in JobsList
- convert test runs to API
- performance test with lots of jobs and runs
- when starting up, cancel and reschedule all future jobs
- add a --since flag, to control how far back to reschedule
- watch jobs for changes
- when a job has changed, cancel and reschedule all future runs?
- sanity checker
  - check for unscheduled runs
  - check for late scheduled runs
  - check for orphaned running runs
  - check for runs that ran late
- test restarting apsis
- define the extension mechanism (program, schedule, etc.)
- kill button for running run
- web UI for ad hoc runs
- document API
- CLUI for testing jobs repo
- tooltip for timestamps with local, UTC, (run-local?), and elapsed times
- factor args out of schedule classes


# Old

- Make RunsSocket replace runs, not stack them.
- Replace RunsSocket with a single ws pubsub protocol.

- Action log for each run.

- API for submitting ad-hoc jobs.
- Command line UI.
- Hot reload jobs via API.
- Clean shutdown.

- When jobs changed, reschedule the docket job.
- When is the job fixed for an inst/run?  At start time?
  - Store job_id instead of job, until that time.

- Round all schedule times to some sane precision?
- Compute elapsed time in UI.
- Time zones in UI.

- Figure out how to handle errors in fetch(), or use something better.
- Better test jobs.
- Figure out what to do about the sanic wildcard route hack.  Submit?
- Webpack setup for web GUI.
- Incremental search on job / instance tables.
- Show when websocket disconnects, and try to reconnect.
- Handle exceptions in API.
- Handle API errors in UI.
- Validate jobs after loading.
- Validation of schedule, results.
- Show API JSON in UI?

- Clean up old files in repo.

- Think about what happens to running jobs when sched is bounced.
- New session / pgroup / ?? for ProcessProgram.
- Login shell for ShellProgram.
- Add env, cwd, and other stuff to ProcessProgram.
- Capture rusage and other usage from ProcessProgram.
- SSH wrapper.

- Auto rerun rules.


cron
- format time with tz
- control precision in time, daytime formats
- parse weekdays (see repo.py)
- load named calendars from files


# agent

- randomize proc_id
- break up `execute()` so that start, wait/update are separated
- async requests in agent client
- serve HTTPS
- access control with secret
- agent kills children and removes directory when shut down
- command/API for starting (if necessary) and connecting to agent
- document it

