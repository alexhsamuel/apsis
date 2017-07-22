- Add randomly failing test job.
- Show multiple runs for an inst.
- Rerun an inst.
- Don't run a job when an inst has succeeded.
- "Run now" button for scheduled run.
- Customize run view for overall, job screen.

- API for submitting ad-hoc jobs.
- Command line UI.

- When jobs changed, reschedule the docket job.
- When is the job fixed for an inst/run?  At start time?
  - Store job_id instead of job, until that time.

- Round all schedule times to some sane precision?
- Figure out how to handle errors in fetch(), or use something better.
- Better test jobs.
- Figure out what to do about the sanic wildcard route hack.  Submit?
- Webpack setup for web GUI.
- Block out web GUI.
- Rename State -> Apsis, or somethign else.
- Rename Inst -> Task, or something else.
- Incremental search on job / instance tables.
- Show when websocket disconnects, and try to reconnect.
- Handle exceptions in API.
- Handle API errors in UI.
- Clean shutdown.
- Hot reload jobs via API.
- Validate jobs after loading.
- Validation of schedule, results.
- Clean up old files in repo.

- Think about what happens to running jobs when sched is bounced.
- New session / pgroup / ?? for ProcessProgram.
- Login shell for ShellProgram.
- Add env, cwd, and other stuff to ProcessProgram.
- Capture rusage and other usage from ProcessProgram.
- SSH wrapper.


cron
- format time with tz
- control precision in time, daytime formats
- parse weekdays (see repo.py)
- load named calendars from files

