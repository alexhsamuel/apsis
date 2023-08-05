Extending Apsis
===============

Apsis can be extended with custom behaviors.  To make extension code available,
simply place it in a module that is available for import from Python, for
instance by installing the code into the active environment (venv or conda), or
by adding the directory containing the module to `PYTHONPATH`.  You can then
refer to your extensions in the Apsis config file or in job config files.


Programs
````````

To add an additional program type to Apsis, extend the `apsis.program.Program`
class and implement its methods.  Ensure that the custom program class is in a
module that is importable by Apsis.  Specify the full import path to the class
in the `type` key.

For example, a custom program class `BatchProgram` in the module `acme.ext` is
used like this in a job config:

.. code:: yaml

    program:
        type: acme.ext.BatchProgram
        # other config keys specific to BatchProgram



Actions
```````

To add an additional action to Apsis, extend the `apsis.action.Action` class and
implement `__call__()`.  Note that each action is run in a separate async tasks,
which means,

1. It must not block the async event loop.

2. Multiple actions may run (async) concurrently.

3. The run may transition while the action is running.  The `Run` object passed
   to the action is a copy, however, and will not reflect further transitions.

Alternately, extend the `apsis.action.ThreadAction` class and implement `run()`.
The implementation should be synchronous and may block.


