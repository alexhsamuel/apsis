# Current

- in agent, SIGCHLD may show up before pid is registered
- don't require run in Program API
- use token to authenticate with agent
- use SSH connection to agent
- configuration
- release
  - update web UI
  - conda recipe
  - intro docs in README
  - job docs
- sudo support in programs
- control page
  - reload jobs
  - restart
  - clear live logs when reconnecting
  - auto-scroll live logs to bottom
  - reconnect live log when disconnected
  - show toast when live log disconnected
- load live runs in the background for the whole app
- time range in runs search: design it better
- a good set of demo jobs
- in collapsed run group, show schedule time of original job
- change --host, --port to --bind
- job YAML template
- favicon
- better rerun model
- indicate a run/job as ad hoc
- in runs list, break out args into columns if showing only one job, or if runs have mostly the same params
- prevent the same instance from running more than once... HOW?
- gzip output
  - in agent
- use flex layout for run list selection controls
- performance test with lots of jobs and runs
- store schedule horizon per (job, schedule) ???
  - limit number of runs scheduled per job
- nicer job output in CLUI
- add a --since flag, to control how far back to reschedule when creating
- live elapsed time in runs list
- live output for running jobs in run view
- watch jobs for changes
- when a job has changed, cancel and reschedule all future runs?
- search, filtering in JobsList
- web UI for showing run, job as JSON
- support multiple outputs per run in API/UI
  - add option to split stdout/stderr
- sanity checker
  - check for unscheduled runs
  - check for late scheduled runs
  - check for orphaned running runs
  - check for runs that ran late
- test restarting apsis
- define the extension mechanism (program, schedule, etc.)
- kill button for running run
- in RunList, if sorted by time, draw a line at now
- web UI for ad hoc runs
- document API
- watch runs live (poll? websocket?) in CLUI
- CLUI for testing jobs repo
- tooltip for timestamps with local, UTC, (run-local?), and elapsed times
- factor args out of schedule classes
- web UI reconnects web socket automatically
- indicate in web UI when a job started late
- move schedule time out of times; rename times → timestamps
- have agent attempt to recover orphaned processes


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

