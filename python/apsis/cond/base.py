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
        Binds the condition to `inst`.

        :param run:
          The run to bind to.
        :param jobs:
          The jobs DB.
        :return:
          An instance of the same type, bound to the instances.
        """


    def check_runs(self, run_store):
        """
        Checks whether all run conditions are met.

        :return:
          True if dependencies are met.
        """



#-------------------------------------------------------------------------------

def _bind(job, obj_args, inst_args, template_args, defs):
    """
    Binds args to `job.params`.

    `obj_args` are the args from the object being bound.  These take precedence
    over other args.  They are templated-expanded with `template_args`.

    `inst_args` are the args from the associated run, to which the object is
    attached.  These are used to fill in args missing from `obj_args`
    automatically.  They are not template-expanded, as the associated run
    is already bound.

    `template_args` are used only for template-expanding `obj_args`.

    :param obj_args:
      Args from the object being bound.
    """
    template_args = {**template_args, **defs.get_for_args(inst_args)}

    def get(name):
        try:
            return template_expand(obj_args[name], template_args)
        except KeyError:
            pass
        try:
            return inst_args[name]
        except KeyError:
            pass
        raise LookupError(f"no value for param {name} of job {job.job_id}")

    return { n: get(n) for n in job.params }


