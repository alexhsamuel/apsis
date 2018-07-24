# Runs

### Persistent run state

Newly scheduled runs come in two flavors:

- "Expected" runs (`run.expected == True`) are scheduled from a job's schedule.
  Such a run is expected in the sense that the job schedule may change between
  now and when the run starts, so the run might be modified or cease to exist.

- Other runs (`run.expected == False`) are scheduled by other mechanisms: ad hoc
  runs, automatic reruns, or manual reruns.  Such a run should start at its
  scheduled time.

The persistent run store is the source of truth for all runs _except_ scheduled,
expected runs.  Expected runs are not persisted when in the schedule state.  

If Apsis is restarted, the new instance will reschedule runs from the job
schedule.  The start time for scheduling is the last time the previous instance
ran scheduled runs.  Any runs since that time are scheduled according to the
current job schedule; if they are scheduled for the past, they are run
immediately.

