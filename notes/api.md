# API endpoints

## Run schema

Immutable:
- run_id
- job_id
- args
- labels (extracted from job metadata)

Immutable but not part of summary:
- program
- conditions
- actions

Mutable on transition only:
- state
- times
- expected

Mutable anytime:
- metadata
- run log
- output


## Messages

A `run_summary` message is sent when a new run is created or when a run
transitions.
```js
{
  "type": "run_summary",
  "run_summary": {
    # Immutable
    "job_id": ...,
    "args": [...],
    "labels": [...],
    # Mutable on transition
    "state": ...,
    "times": {...},
    "expected": true,  # optional; omitted if false
  }
}
```

```js
{
  "type": "run",
  "run": {
    ..., # as per run_summary
    "program": {...},
    "conditions": {...},
    "actions": {...},
  }
}
```

```js
{
  "type": "run_delete",
  "run_id": ...
}
```


A `run_metadata` message carries the entire latest metadata for a run.
```js
{
  "type": "run_metadata",
  "run_id": ...,
  "metadata": {...},
}
```

An `run_output` messages carries partial or complete output data for a run.
```js
{
  "type": "run_output",
  "run_id": ...,
  "output_id": "output",
  ... # TBD
}
```

A `run_log` message carries the entire run log for a run.
```js
{
  "type": "run_log",
  "run_id": ...,
  "run_log": [
    {
      "timestamp": ...,
      "message": ...,
    },
    ...
  ]
}
```

