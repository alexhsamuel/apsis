.. _conditions:

Conditions
==========

A _condition_ is a boolean predicate that must be satisfied before Apsis starts
a run.

When a run's scheduled time arrives, Apsis transitions the run to the
**waiting** state, and begins checking the run's conditions.  All conditions
must be satisfied before Apsis transitions the run from **waiting** to
**starting**.

Apsis assumes that a once a condition is satisfied, it remains so permanently,
so you can think of a condition as a gate or a boolean step function.

Apsis evaluates multiple conditions in the order specified; only after the first
condition is satisfied does Apsis check the second, etc.

Condition types are listed below.


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


