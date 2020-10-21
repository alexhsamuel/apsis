Configuring Jobs
================

Jobs are configured by files in the jobs directory.  The jobs directory may
contain subdirectories, to organize jobs.  Each job file uses the `.yaml` file
suffix, and specifies one job, with a unique job ID, in YAML format.

The Apsis config file specifies the location of the jobs directory; see
[[config]].

Each job includes:

- a job ID, for referring to the job
- a list of parameter names (which may be empty)
- a program, which specifies what to run 
- a schedule, which specifies when to schedule runs
- optionally, conditions that must be met for a run
- optionally, actions to take when a run changes state


Job ID
------

The job's ID is given by the path under the jobs directory, with the `.yaml`
suffix removed.  For example, if the jobs directory is `/path/to/jobs`, the job
file `/path/to/jobs/data/pipeline/start.yaml` has the job ID
`data/pipeline/start`.


Parameters
----------

A job may be parametrized, to customize the behaviors of its runs.  Each run of
a job will provide an argument for each parameter.  Arguments are always
strings, though the job may interpret parameters specially.

The `params` key takes a list of parameter names.  For example,

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

The `schedule` key pspecifies when new runs are created and for when they are
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
for a condition, the run is in the _waiting_ state.  Multiple conditions may
apply to a run; it is _waiting_ until all are satisfied.

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



Reruns
------

FIXME: Write this.


Actions
-------

FIXME: Write this.


