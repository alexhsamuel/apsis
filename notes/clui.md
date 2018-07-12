
- `apsis jobs list`

  List all jobs.

- `apsis job JOB-ID show`

  Show a job specification.

- `apsis job JOB-ID runs`

  Show runs of a job.

- `apsis run RUN-ID show`

  Show a run.



<hr>

```
apsis job                               # list jobs
apsis job JOB-ID                        # show job
apsis run RUN-ID                        # show run
apsis run RUN-ID output                 # fetch output
apsis run RUN-ID rerun                  # rerun
apsis run RUN-ID start                  # start now
apsis schedule -- CMD ...               # schedule an ad hoc run
apsis schedule --at TIME -- CMD ...     # schedule an ad hoc run for later
```

```
apsis jobs                              # list jobs
apsis job JOB-ID                        # show job
apsis run RUN-ID                        # show run
apsis run RUN-ID --watch                # show run and wait for updates
apsis output RUN-ID                     # fetch output
apsis rerun RUN-ID                      # rerun
apsis start RUN-ID                      # start now
apsis schedule now CMD ...              # schedule an ad hoc run
apsis schedule TIME CMD ...             # schedule an ad hoc run for later
```

