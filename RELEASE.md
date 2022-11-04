# In progress

### Skipped runs

- Add the _skipped_ state and _skip_ operation.  Remove the _cancel_ operation;
  superceded by _skip_.
- Add `run` param to the signature for `Condition.check_runs()`.  Custom
  condition classes need to be updated.
- Add support for inducing a transition from `Condition.check_runs()` by
  returning a `Condition.Transition` value.
- Add the `skip_dependency` condition type.

### Config

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


