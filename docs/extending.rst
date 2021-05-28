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



