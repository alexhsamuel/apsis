.. _config:

Configuring Apsis
=================

Configure the Apsis server by writing a YAML configuration file and specifying
it with the `\--config` command line option.  You can override individual
configurations using the `\--override NAME=VALUE` command line option; use dotted
names like `runs.lookback=86400` to specify heirarchical configuration names.

A sample file illustrating all config variables and their default values is
below.  Relative paths are interpreted relative to the path containing the
config file.

.. code:: yaml

    jobs: ./jobs                # path
    database: ./apsis.db        # path

    runs:
      lookback: null            # seconds

    schedule:
      since: null               # now, or YYYY-MM-DDTHH:MM:SSZ
      max_age: null             # seconds
      horizon: 86400            # seconds

    waiting:
      max_time: null            # seconds

    program_types:
      # ...

    schedule_types:
      # ...

    action_types:
      # ...

    host_groups:
      # ...


For durations in seconds, you may also use durations like `30s`, `10 min` (600
seconds), `1.5h` (5400 seconds), and `1 day` (86400 seconds).


Files
-----

`jobdir` specifies the path to the directory containing job files.

`database` specifies the path to the database file containing run state.


Runs
----

`runs.lookback` specifies the maximum run age, in seconds.  Runs older than this
are not held in memory and are not visible in user interfaces.  They are
retained in the database file, however.


Schedule
--------

`schedule.since` specifies since when to schedule runs *on startup*.  This can
cause Apsis to skip over runs that would have been scheduled in the past, were
Apsis running at the time.

- `null`: schedule runs since the last time Apsis was run with the database
  file.  If the database file is used for the first time, schedule runs starting now.

- `now`: schedule runs starting now.

- A time with time zone, e.g. `2023-04-27T16:00:00Z`.

`schedule.max_age` sets a limit on how long Apsis can schedule a run after its
nominal schedule time.  Apsis fails if it ever tries to schedule a run older
than this.  This prevents very old runs from running spuriously.

`schedule.horizon` specified how far foward in time, in seconds, to schedule new
runs.


Waiting
-------

`waiting.max_time` limits the time, in seconds, a single run can be in the
waiting state.  After this time, Apsis transitions the run to the error state.


Types
-----

A program may specify a program, schedule, or action type by full Python name.  This allows
you to use a custom program type to extend Apsis, as long as the class is importable by
Apsis.  You may also configure shorter aliases for types:

.. code:: yaml

    program_types:
      foo_shell: foo.apsis.extension.programs.Shell
      foo_cmd: foo.apsis.extension.programs.Command

Likewise for schedules and actions:

.. code:: yaml

    schedule_types:
      foo_schedule: foo.apsis.extension.schedule.MySchedule

    action_types:
      foo_action: foo.apsis.extension.action.MyCustomAction


Host groups
-----------

A host groups enables a job to run a program on one of a group of hosts, rather
than on a fixed host.  You can specify a host group name in place of a host
name.  Host groups are configured globally.

The group type, `round-robin` or `random`, controls how hosts are chosen from
the group.

A single host name is effectively a host alias.

.. code:: yaml

    host_groups:
      my_group:
        type: round-robin
        hosts:
        - host1.example.com
        - host2.example.com
        - host3.example.com

      my_alias: host4.example.com


