### Create a run

To create a run of an existing job:
```
POST /api/v1/runs
request = {
  "job_id": "JOB-ID",
  "args": {
    "PARAM": "VALUE",
    ...
  },
  "times": {
    "schedule": "TIME"
  }
}
```

If the schedule time is omitted, the run is run immediately.  Args may be
omitted if empty.

To create an ad hoc job and a run of it:
```
POST /api/v1/runs
request = {
  "job": {
    ...
  },
  "args": {
    "PARAM": "VALUE",
    ...
  },
  "times": {
    "schedule": "TIME"
  }
}
```

The format of the job is the same as job files in the job repo.  As above, the
run is run immediately if the schedule time is omitted.  Args is usually not
required and may be omitted.

