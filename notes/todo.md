# Current

- in agent, SIGCHLD may show up before pid is registered

- clean up command line UI
  - implement `apsis runs --times`
  - nicer run list
  - nice job display
- convert `run.times` to log, with schema (timestamp, message, state)
  - show history in CLUI
  - retire run/transition message
  - retire times in run?  or hide from UI
- `apsisctl` script 
  - check job *dir*
  - migrate apsis.db
- configuration
  - provide a way to add functions to jinja2 eval namespace
- refactor runs websocket into event stream
  - contains:
    - run updates
    - output updates
    - job refresh
    - other things?
  - watch runs live in CLUI
  - connection indicator in web UI
- watch jobs for changes
- when a job has changed, cancel and reschedule all future runs?
- search, filtering in JobsList
- gzip output
  - in agent
- release
  - update web UI
  - conda recipe
  - intro docs in README
  - job docs
- sudo support in programs
- normalize environment for another user, locally and by ssh
- use token to authenticate with agent
- SSL for Apsis
- control page
  - reload jobs
  - clear live logs when reconnecting
  - auto-scroll live logs to bottom
  - reconnect live log when disconnected
  - show toast when live log disconnected
- kill button for running run
- factor out Vue API client code into module
  - error handling
- integrate [ansi-to-html](https://www.npmjs.com/package/ansi-to-html) for run output
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
- use flex layout for run list selection controls
- performance test with lots of jobs and runs
- store schedule horizon per (job, schedule) ???
  - limit number of runs scheduled per job
- add a --since flag, to control how far back to reschedule when creating
- live elapsed time in runs list
- live output for running jobs in run view
- web UI for showing run, job as JSON
- support multiple outputs per run in API/UI
  - add option to split stdout/stderr
- sanity checker
  - check for unscheduled runs
  - check for late scheduled runs
  - check for orphaned running runs
  - check for runs that ran late
- define the extension mechanism (program, schedule, etc.)
- in RunList, if sorted by time, draw a line at now
- web UI for ad hoc runs
- document API
- tooltip for timestamps with local, UTC, (run-local?), and elapsed times
- factor args out of schedule classes
- web UI reconnects web socket automatically
- indicate in web UI when a job started late
- move schedule time out of times; rename times → timestamps
- have agent attempt to recover orphaned processes

- Change agent so that client-initiated commands are always via SSL.  Implement
  webhook for return notications, like process completion.  See [[ssl.md]].


# Old

- Make RunsSocket replace runs, not stack them.
- Replace RunsSocket with a single ws pubsub protocol.

- API for submitting ad-hoc jobs.
- Hot reload jobs via API.

- When jobs changed, reschedule the docket job.
- When is the job fixed for an inst/run?  At start time?
  - Store job_id instead of job, until that time.

- Round all schedule times to some sane precision?
- Compute elapsed time in UI.

- Figure out how to handle errors in fetch(), or use something better.
- Webpack setup for web GUI.
- Incremental search on job view.
- Show when websocket disconnects.
- Handle exceptions in API.
- Handle API errors in UI.
- Validate jobs after loading.
- Validation of schedule, results.
- Show API JSON in UI.

- Clean up old files in repo.

- New session / pgroup / ?? for ProcessProgram.
- Add env, cwd, and other stuff to ProcessProgram.
- SSH wrapper.


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

