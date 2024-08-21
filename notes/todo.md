# Live updates

WebSocket API for web UI:
- run updates for all runs (as current)
- run log updates for a single run
- run data updates for a single run
- agent changes: connect, disconnect, timeout
- job changes

Persistent connection:
- run changes (run summaries only)
- job changes
- Procstar connection changes
- Apsis log (if we keep this)

Transient connection (single run):
- run log updates
- run output data updates
- run metadata updates


### The Plan

- [x] design internal run publisher protocol
  - use the same JSO sent from API endpoints
- [x] new `/summary` websocket endpoint for transitions only
- [x] add job updates to `/summary`
- [x] in web UI, put jobs in store and process updates
- [x] merge processing of job and run messages
- [x] new job message
- [x] delete job message
- [x] move run operations to UIs
- [x] clear store.state.{runs,jobs} on ws reconnect

- [x] remove `run.message` from JSON run summary
- [x] retire `RunsSocket` in favor of `JsonSocket`
- [x] retire `/ws/runs/` endpoint
- [x] retire `_jso_cache`
- [x] add Procstar connection updates to summary endpoint
  - [x] move Procstar agent `SERVER` to `Apsis` object
  - [x] clean up `Apsis` object tasks
  - [x] clean up message and variable names
- [x] retire `RunStore.query_live`
- [x] add publisher stats to `Apsis.get_stats`
- [x] clean up `RunStore`, merge `_query_filter`, remove `shutdown`
- [x] break out wait loop into fn

- [x] add `/ws/run/<run_id>` endpoint
  - [ ] option to send initial values
  - [x] metadata updates
  - [ ] run log updates
  - [ ] program output updates
  - [ ] clean up API endpoints we don't need anymore
- [x] roll in Procstar agent changes to `/summary`
- [ ] roll in, or get rid of, log socket
- [ ] add live endpoints to `Client`
- [ ] live updates in CLUI
  - [ ] single run transition
  - [ ] output
  - [ ] run log


# Cleanup

### Schema

- Remove `message` from run JSON and `runs` table.

- Move metadata out of `runs` into its own table, along with any other column
  that isn't part of the run summary.

- Clean up `rerun` column as well.

- Rename `run_history` to `run_log`.

### Other

- To finish `check-job`, we need to remove the program, schedule, action, cond
  aliases from `config.yaml` and move them to a config file specific to the job
  dir.

- Factor loop watchers (`log.critical`) into a common pattern.

- Clean up the restore task.


# Idle thoughts

Change scheduler, scheduled, wait loops into async iters that return
instructions to Apsis, who then applies them, rather than applying them directly.


# Tools

- https://rich.readthedocs.io/en/latest/index.html for console output
- https://github.com/wildfoundry/dataplicity-lomond for websockets


# Redis

- refactor on master:
  - split out run ID allocator
  - configure Redis instance in config.yaml
  - add a `RedisRunStore` and populate it from `RunStore.add` / `.remove`
  - add async `query()` and `subscribe()` methods


# Docs

- organize config into chapter?
- schedule config
- actions
- CLUI
- web UI


# Current

- #165: conditional skip runs, e.g. skip if running
- #164, #152: limit duration of run in waiting state
- #156: auto-archive old runs

- in ora, truncate 0s from `Time.__str__` and `Daytime.__str__`

- support configured extension symbols in `template_expand`

- "wait" functionality in CLUI
  - `apsis wait r12345`
  - `apsis output --wait r12345`
  - `apsis run --wait ...`
  - `apsis run --output ...`

- rip out reruns, replace with actions
- document reruns
- document actions

- check out: https://beepb00p.xyz/scheduler.html (and comment?)
- check out: https://github.com/jhuckaby/Cronicle
- check out: https://github.com/huginn/huginn
- check out: https://apscheduler.readthedocs.io/en/stable/

- bug: don't fuzzy-match job IDs in API when called from web UI

- favicon: animated!

- better action UI
  - proper button
  - confirmation dialog
  - no redirect

- add date to apsis log

- add version to web UI

- migrate to aiohttp

- label for ad-hoc jobs

- attach job to run when scheduling, rather than loading jobs later

- job label search

- schedule time jitter

- runs filter
  - remove time, state filter from query args
  - make time, state filter persistent?  (cookie?)

- path navigation
  - proper programmatic API in runFilter, to build query?
  - handle "/path" terms in search box specially

- better env vars in running programs, ala `APSIS_RUN_ID`.

- agent cleanup
  - add endpoint to forefully shut down
  - automatically clean up abandoned processes after a certain time
  - occasionally poll childen explicitly, to catch silently died processes
  - shut down agent cleanly, including canceling shutdown task

- send debug log to file, from config

- handle more runs
  - query db for older runs instead of holding them in memory (not possible?)
  - in job view, include time limitation

- check out: FastAPI, uvicorn, Starlett

- clean up command line UI
  - implement `apsis runs --times`
  - nicer run list
  - nice job display

- convert `run.times` to log, with schema (timestamp, message, state)
  - retire run/transition message
  - retire times in run?  or hide from UI

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

- normalize environment for another user, locally and by ssh

- SSL for Apsis

- control page
  - reload jobs
  - clear live logs when reconnecting
  - auto-scroll live logs to bottom
  - reconnect live log when disconnected
  - show toast when live log disconnected

- factor out Vue API client code into module
  - error handling

- integrate [ansi-to-html](https://www.npmjs.com/package/ansi-to-html) for run output

- a good set of demo jobs

- in collapsed run group, show schedule time of original job

- change --host, --port to --bind

- job YAML template

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


# wait timeout + skip

- max time in waiting state
  - global
  - per job [where?]
- max time (since schedule) per condition
- max run time (since start)

### skip

Let `Condition.skip_runs()` or `Condition.skip()` return a code indicating skip?

Ass a "skipped state?  Or let the condition choose one of the others?

Provide user actions to transition a run to skipped?

