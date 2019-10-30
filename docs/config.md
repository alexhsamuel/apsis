# Configuration

Relative paths are interpreted relative to the path containing the config file.

```yaml
# The path to the directory containing job definitions.
jobs: /path/to/jobdir

# Lookback in secs for old runs.  At startup, only runs younger than this are
# loaded from the run database.
runs_lookback: 2592000  # 30 days

# Refuse to schedule runs older than this.
schedule_max_age: 86400  # 1 day

# The path to the database containing Apsis state.  Use "apsisctl create" to
# create a new state database.
database: /path/to/apsis.db
```




