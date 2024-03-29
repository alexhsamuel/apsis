Configuring Jobs
================

Jobs are configured by files in the jobs directory.  The jobs directory may
contain subdirectories, to organize jobs.  Each job file uses the `.yaml` file
suffix, and specifies one job, with a unique job ID, in YAML format.

The Apsis config file specifies the location of the jobs directory; see
[[config]].

A job config contains these top-level keys:

- `params` (optional)
- `program`, which specifies what to run 
- `schedule`, which specifies when to schedule runs
- `metadata` (optional), additional information not interpreted by Apsis
- `conditions` (optional) that must be met for a run
- `actions` (optional) to take when a run changes state

For durations in seconds, you may also use durations like `30s`, `10 min` (600
seconds), `1.5h` (5400 seconds), and `1 day` (86400 seconds).


Job ID
------

The job's ID is given by the path under the jobs directory, with the `.yaml`
suffix removed.  For example, if the jobs directory is `/path/to/jobs`, the job
file `/path/to/jobs/data/pipeline/start.yaml` has the job ID
`data/pipeline/start`.


Params
------

The `params` key in the job config takes a list of parameter names.  For
example,

.. code:: yaml

    params:
      - date
      - message

or equivalently,

.. code:: yaml

    params: ["date", "message"]

If `params` is omitted, the job has no parameters.

Parameters aren't required; a job without parameters can be run repeatedly, just
like a cron job.


Program
-------

The `program` key program describes how a run executes.  Apsis provides several
types of programs, and you may extend Apsis with additional program types as
well.

See :ref:`programs` for more information.


Schedule
--------

The `schedule` key specifies when new runs are created and for when they are
scheduled.

A job may have a single schedule, given as a dict, or multiple schedules, as a
list of dicts.

.. code:: yaml

    # Single schedule
    schedule:
        type: interval
        interval: 3600

    # Two schedules
    schedule:
      - type: interval
        interval: 3600
      - type: daily
        tz: UTC
        daytime: 12:00:00

See :ref:`schedules` for more information.


Metadata
--------

A job can store arbitrary metadata, such as descriptive text, tags, and operator
instructions.  The `metadata` key accepts arbitrary subkeys.  None affect how
runs of the job are executed.

Apsis does understand certain metadata keys.  The `description` key contains
descriptive Markdown text shown in the UI.

.. code:: yaml

    metadata:
        description: |
            Daily cleanup job.

            Removes temporary files that have been created within the last 24
            hours.

The `labels` key is an array of string labels, also shown in the UI.

.. code:: yaml

    metadata:
        labels:
            - test
            - blue-team

Any other metadata keys are preserved but ignored by Apsis.


Conditions
----------

A condition temporarily prevents a scheduled run from starting.  While waiting
for a condition, the run is in the **waiting** state.  Multiple conditions may
apply to a run; it is **waiting** until all are satisfied.

Max running jobs
''''''''''''''''

The `max_running` condition causes a run to wait as long as there are too many
other running runs with the same job ID and arguments.  For `max_running: 1`,
there may be only one such running job.

.. code:: yaml

    condition:
        type: max_running
        count: 1


Dependencies
''''''''''''

The `dependency` condition causes a run to wait until another run exists in a
given state.  Specify the job ID of the dependency, and any arguments.

.. code:: yaml

    condition:
        type: dependency
        job_id: "previous job"
        args:
            label: foobar

The arguments are template-expanded.  If the dependency job shares a param with
the dependent job, it may be omitted; the same arg is used.

By default, the dependency causes the run to wait until a matching **success**
run arises.  You can specify another target state or set of states:

.. code:: yaml

    condition:
        type: dependency
        job_id: "previous job"
        args:
            label: foobar
        states: ["success", "failure"]

This condition does not actually create the dependecy run.  You must create that
run elsewhere, usually by scheduling it.  If the run doesn't exist at all, the
dependency condition will wait until `waiting.max_time` elapses, and then
transition the run to **error**.

To check that a corresponding dependency run exists at all, using set `exist` to
true.  With this, the condition transitions the run to **error** _immediately_
if the run does not exist, or if it has completed unsuccessfully.  If a run
exists that may still transition to **success**, the condition waits as usual.

.. code:: yaml

    condition:
        type: dependency
        job_id: "previous job"
        args:
            label: foobar
        exist: true

Instead of true, you may provide a set of states in which the run must exist.
The default is state from which one of the target states is reachable.


Skipping Duplicates
'''''''''''''''''''

The `skip_duplicate` condition causes a run to transition to the **skipped**
state if there is another run with the same job ID and arguments that is either
waiting or running.

.. code:: yaml

    condition:
        type: skip_duplicate

By default, Apsis looks for other runs in the **waiting**, **starting**, or
**running** states to determine whether to skip this run.  You can override this
with `check_states`.  You can also specify a different (finished) state to
transition to.  For example, to transition a run to **error** if there is already
another run in either of the **failure** or **error** states:

.. code:: yaml

    condition:
      type: skip_duplicate
      check_states: [failure, error]
      target_state: error

As with other conditions, this condition is applied only when a run is in the
**waiting** state.


Actions
-------

FIXME: Write this.


.. _binding:

Binding
-------

Apsis creates specific runs for a job, according to the job's schedule.  When
Apsis creates a run, it **binds** the run's arguments in the program and
conditions.  Each string-valued config field is expanded as a `jinja2 template
<https://jinja.palletsprojects.com/en/2.11.x/templates/>`_.  The run's args are
available as substitution variables.

For example, consider this job config:

.. code:: yaml

    params:
    - color
    - fruit

    program:
        type: shell
        command: "echo The color of {{ fruit }} is {{ color }}."

When Apsis creates a run with `color: red` and `fruit: apple`, it expands the
program to,

.. code:: yaml

    program:
        type: shell
        command: "echo The color of apple is red."

The contents of a `{{ ... }}` expansion is evaluated as a `jinja2 expression
<https://jinja.palletsprojects.com/en/3.1.x/templates/#expressions>`_.  The
following additional Ora types and functions are available:

- `Date <https://ora.readthedocs.io/en/latest/dates.html#dates>`_
- `Daytime`
- `Time <https://ora.readthedocs.io/en/latest/times.html#times>`_
- `TimeZone <https://ora.readthedocs.io/en/latest/time-zones.html#time-zone-objects>`_
- `get_calendar <https://ora.readthedocs.io/en/latest/calendars.html#finding-calendars>`_
- `from_local <https://ora.readthedocs.io/en/latest/localization.html#local-to-time>`_
- `to_local <https://ora.readthedocs.io/en/latest/localization.html#time-to-local>`_

These functions and types allow you to perform time computations on program and
condition dates and times.  For example, this job has a dependency on another
job *load data*.  Each run of this job is labeled with a date, and depends on a
*load data* run with the previous date, according to the *workdays* calendar.

.. code:: yaml

    params: [region, date]

    ...

    condition:
        type: dependency
        job_id: load data
        args:
            date: {{ get_calendar('workdays').before(date) }}

Keep in mind that Apsis run arguments are always strings, so Apsis converts the
result using `str`.

