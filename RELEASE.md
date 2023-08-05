# v0.19

- Add `apsis.action.ThreadAction`, a base class for an action that runs
  synchronously in a separate thread.
- Add `/api/v1/live` and `/api/v1/stats` endpoints, to monitor basic liveness
  and stats, respectively.
- Add estimate of async event loop latency to stats.


# v0.18

- Add support for async conditions.  Custom conditions need to be updated
  accordingly; see [#278](https://github.com/alexhsamuel/apsis/pull/278).
- Polling of agent programs is now async.  This allows more concurrently running
  programs without degraded performance.
- Update build config to `pyproject.toml`.


# v0.17.0

- The config `runs_lookback` is now `runs.lookback`.  When configured, Apsis
  retires older runs from memory runs while running.
- The internal program `ArchiveProgram` moves old runs out of the Apsis database
  into a separate archive database file.  This also retires the old runs from
  memory.  This program replaces the old `apsisctl migrate` manual process.
- The internal program `StatsProgram` collects and writes Apsis usage stats.
  Apsis no longer logs stats to its own log.
- The Python builtin `format` and the Ora functions `from_local` and `to_local`
  are available in jinja2 expressions when binding jobs.
- The `shell` and `program` program types now accept a `timeout`.
- Durations in the Apsis config file and in job definitions now support values
  with units such as `10 min`, `8h`, and `1 day`.


# v0.16.0

- The web UI has been substantially improved.  The new design permits navigation
  of a much larger number of runs, without displaying them all at one time.
- Filters for runs and views are more flexible and explicit.  Click help icons
  for explanations.
- The URL scheme for runs and views filters has changed substantially.  Any
  bookmarked or otherwise saved URLs to these views won't work anymore.
- `apsisctl check-jobs` checks conditions (including dependencies) and actions
  for missing and extraneous args.  #245


# v0.15.0

- Add a "Schedule Run" frame to the web UI job view, for manual scheduling.
- Apsis now compresses program outputs with Brotli before storing to the
  database.  The HTTP service also returns Brotli-compressed output, if the user
  agent supports this encoding.


# v0.14.0

- Add the _skipped_ state and _skip_ operation.  Remove the _cancel_ operation;
  superceded by _skip_.
- Add `run` param to the signature for `Condition.check_runs()`.  Custom
  condition classes need to be updated.
- Add support for inducing a transition from `Condition.check_runs()` by
  returning a `Condition.Transition` value.
- Add the `skip_dependency` condition type.
- Group scheduler config under `schedule` key.  Add `schedule.horizion` config.
  Rename `schedule_max_age` to `schedule.max_age`.


# v0.13.1

- Remove UIkit from the web UI, for performance.  Minor visual and behavioral changes.
- Various other performance fixes to web UI and supporting HTTP API.
- Fix #181, incorrect job fuzzy match in web UI.


# v0.13.0

- Add "no-op" program type.
- Add `waiting.max_time` config to impose maximum waiting time on all runs.
- Log basic stats as a JSON document in a minutely INFO log line.


