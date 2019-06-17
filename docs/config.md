# Configuration

Relative paths are interpreted relative to the path containing the config file.

```yaml
# The path to the directory containing job definitions.
jobs: /path/to/jobdir

# Lookback in secs for old runs.
# Currently, applied when loading runs from database at startup.
runs_lookback: 2592000  # 30 days

# The path to the database containing Apsis state.  Use "apsisctl create" to
# create a new state database.
database: /path/to/apsis.db
```

