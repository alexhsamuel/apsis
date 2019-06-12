Configuring Jobs
================

Specify a job with a file in the jobs directory.  The Apsis config file
specifies the path to the jobs directory, by default `jobs/` next to the Apsis
config file itself.

Each job file specifies one job, with a unique job ID.  The job may be scheduled
to run many times, however, with various arguments,

Job ID
------

The job's ID is given by the filename, without the .yaml extension.

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

If `params` is omitted, the job has no parameters.  Parameters aren't required;
a job without parameters can be run repeatedly, just like a cron job.

    
Metadata
--------

A job can store arbitrary metadata, such as descriptive text, tags, and operator
instructions.  The `metadata` key accepts arbitrary subkeys.  Currently, Apsis
only understands the `description` metadata key; others are preserved but not
used.

.. code:: yaml

    metadata:
        description: |
            Daily cleanup job.

            Removes temporary files that have been created within the last 24
            hours.


Program
-------

A job's program describes how the job executes.  Apsis provides several types of
programs, and you may implement additional program types as well.

The most common program type is a shell command.  Use the `program` tag, and
simply specify the shell command as a string.

.. code:: yaml

    program: "/bin/echo 'Hello, world!'"

Be careful of YAML's string quoting rules.  Multiple-line commands or scripts
are allowed.  Apsis runs the script you specify directly in bash.

Apsis provides other types of programs too, and a job's programs may access
argument values and other special features.  See :ref:`programs` for more
information.


Schedule
--------

FIXME: Write this.


Preconditions
-------------

A precondition temporarily prevents a scheduled run from starting.  While
waiting for a precondition, the run is in the _waiting_ state.  Multiple
preconditions may apply to a run; it is _waiting_ until all are satisfied.

Max running jobs
''''''''''''''''

The `max_running` precondition causes a run to wait as long as there are too
many other running runs with the same job ID and arguments.  For `max_running:
1`, there may be only one such running job.

.. code:: yaml

    precondition:
        type: max_running
        count: 1


Dependencies
''''''''''''

The `dependency` precondition causes a run to wait until another run exists in
a given state.  Specify the job ID of the dependency, and any arguments.

.. code:: yaml

    precondition:
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


