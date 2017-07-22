- Split up to_jso() stuff.
  - API
  - Serialization for file formats.
- Add randomly failing test job.
- Show multiple runs for an inst.
- Rerun an inst.
- Don't run a job when an inst has succeeded.
- "Run now" button for scheduled run.
- Customize run view for overall, job screen.
- Command line UI.
- API for submitting ad-hoc jobs.
- Round all schedule times to some sane precision?
- Figure out how to handle errors in fetch(), or use something better.
- Better test jobs.
- Figure out what to do about the sanic wildcard route hack.  Submit?
- Webpack setup for web GUI.
- Block out web GUI.
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


cron
- format time with tz
- control precision in time, daytime formats
- parse weekdays (see repo.py)
- load named calendars from files

