# API endpoints

## Messages

```js
{
  "type": "transition",
  "run_summary": {
    "run_id": ...,
    "job_id": ...,
    "args": [...],
    "state": ...,
    "times": {...},
    "labels": [...],
    "expected": true,  # optional; omitted if false
  }
}
```



A `metadata` message carries the entire latest metadata for a run.
```js
{
  "type": "metadata",
  "run_id": ...,
  "metadata": {...},
}
```

An `output` messages carries partial or complete output data for a run.
```js
{
  "type": "output",
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

