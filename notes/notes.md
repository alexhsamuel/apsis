# Scheduled stop

THIS IS CORRECT:
```yaml
program:
  type: agent
  argv: ["/path/to/my/service", "--foreground"]
  stop:
    signal: SIGTERM
    grace_period: 1m

schedule:
  start:
    type: interval
    interval: 1h
  stop:
    type: duration
    duration: 30m
```



# SQLite

Performance test of appending to string fields, in `work/sqlite-concat.py`.

```py
with engine.begin() as con:
    con.execute("UPDATE data SET data = data || ?", (data, ))
```

The first 1 kB append takes 2 ms.  At 1 MB, the append takes 20 ms.  Appears to
be roughly linear.  Same for both string and binary columns.  Timed on purslane.

### Backup / replication

See https://github.com/benbjohnson/litestream




# Jitter

Schedule jitter risks losing runs if the jitter is nondeterministic-- if the
scheduler is restarted before the jittered run starts, and on restart a new
jitter value is used that places the run's start time before the clock time, the
run will be skipped.

To get around this, make the jittered schedule time sequence deterministic using
RNG seeding.  The seed will need to incorporate some hash of the job and its
params; otherwise two similar schedules of the same job will have identical
jittered time sequences, which is exactly not what you want. 

This probably needs to be done at the scheduler level, not in individual
schedules.


# Tricks

Cancel all waiting runs:
```sh
runs="$(apsis runs --state waiting --format json | jq -r 'keys[] as $k | "\($k)"' )"
for run in $runs; do apsis cancel $run; done
```


# Memory use

### Per run

Baseline:
```
runs / day: 41516
mem  / day: 1.39 GB
mem  / run: 35.1 KB
```

- Add `Run.__slots__`.

- `Run.times` causes a 296 B alloc on the first insert.  Get rid of it, replace
  with two fixed attributes, for the displayed schedule and start times.
  (Though this is fixing display logic into the schema...)

  Alternately, can the run log fill the bill?  Or perhaps this is too expensive
  to reconstruct from.

