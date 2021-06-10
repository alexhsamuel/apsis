from   apsis.lib.json import TypedJso
from   apsis.runs import template_expand

#-------------------------------------------------------------------------------

class Condition(TypedJso):
    """
    A boolean condition that blocks a run from starting.  The run waits until
    the condition evaluates true.
    """

    TYPE_NAMES = TypedJso.TypeNames()

    def bind(self, run, jobs):
        """
        Binds the condition to `run`.

        :param run:
          The run to bind to.
        :param jobs:
          The jobs DB.
        :return:
          An instance of the same type, bound to the run.
        """


    def check_runs(self, run_store):
        """
        Checks whether all run conditions are met.

        :return:
          True if dependencies are met.
        """



