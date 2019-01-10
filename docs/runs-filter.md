The mini language for filtering runs.

The string is separated into search terms by splitting on whitespace, except
honoring double quotes.

Each term is parsed as follows:

- `ARG=VAL`: Matches a run for which `ARG` is an arg and contains `VAL` as a
  substring.
  
- `ARG=`: Matches a run for which `ARG` is defined.

- `JOB`: Matches a run whose job name contains `JOB` as a substring.

- `state:S1,S2`: Matches a run in state S1 or S2.  Each may be a state name
  ("scheduled", "success", ...) or an unambiguous prefix.

- `!TERM`: Inverts any valid `TERM`.

