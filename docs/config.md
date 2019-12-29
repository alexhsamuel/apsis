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


### Host groups

A host groups enables a job to run a program on one of a group of hosts, rather
than on a fixed host.  You can specify a host group name in place of a host
name.  Host groups are configured globally.

```yaml
host_groups:
  # Group of three hosts.
  my_group:
  - host1
  - host2
  - host3

  # Group of a single host; effectively an alias.
  my_alias: host4
```

The default behavior is to choose a host at random for each run.  For
round-robin scheduling,
```yaml
host_groups
  my_group:
    type: round-robin
    hosts:
    - host1
    - host2
    - host3
```


