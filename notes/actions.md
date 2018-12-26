# Config

```yaml
action:
- type: successor
  state: success
  job_id: close day
  args:
  - strat: "{{ strat }}"  # implied?
  - date: "{{ date + cal(strat).DAY }}"
```


### Successors

```yaml
successor:
- job_id: close day
  args:
  - strat: "{{ strat }}"  # implied?
  - date: "{{ date + cal(strat).DAY }}"
```


# Job relationship models

For reference, some of the ways of modeling relationships among jobs.

1. _Successors_: A job specifies successor jobs to be scheduled (or run
   immediately) when the job succeeds.
   
1. _Predecessors_: A job specifies predecessor jobs after which it is to be run
   immedidately.  This is conceptually identical to _successors_, except the
   relationship is specified on on the later job rather than the earlier.  
   
1. _Preconditions_: A job may specify external conditions.  These must be
   satisfied before a run can start.  The scheduler polls or otherwise monitors
   these conditions for readiness.

1. [Tidal] _Dependencies_: A job specifies other jobs that it depends on.  Each
   of its run is scheduled independently, but is blocked until the dependencies
   on other runs are satisfied.  This model is a special case of
   _Preconditions_, with a run's dependencies specified in terms of states of
   other runs.

1. _Pipelines_: Jobs are modeled explicitly as pipelines.

