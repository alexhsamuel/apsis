import asyncio
from   dataclasses import dataclass

from   apsis.lib import py
from   apsis.lib.json import TypedJso, check_schema
from   apsis.lib.timing import LogSlow
from   apsis.runs import Run, template_expand

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


    @dataclass
    class Transition:
        """
        The run should transition to `state`.
        """
        state: Run.STATE
        reason: str = None



#-------------------------------------------------------------------------------

class PolledCondition(Condition):

    # Poll inteval in sec.
    poll_interval = 1

    async def check(self):
        """
        Checks if conditions have been met and the run is ready to start.

        :return:
          `True` if the run is ready, `False` otherwise, or `Transition` to
          cause the run to transition to a new state.
        """
        return True


    async def wait(self):
        """
        Waits for the condition to complete.

        :param timeout:
           Max time to wait, or none for no timeout.
        :return:
          `True` if the run is ready or `Transition` to cause the run to
          transition to a new state.
        """
        while True:
            with LogSlow(f"checking cond: {self}", 0.005):
                result = await self.check()
            if result is False:
                await asyncio.sleep(self.poll_interval)
            else:
                return result



#-------------------------------------------------------------------------------

class RunStoreCondition(Condition):

    async def wait(self, run_store):
        """
        Checks if run-based conditions have been met and the run is ready to
        start.

        :return:
          `True` if the run is ready, `False` otherwise, or `Transition` to
          cause the run to transition to a new state.
        """
        return True



#-------------------------------------------------------------------------------

def _bind(job, obj_args, inst_args, bind_args):
    """
    Binds args to `job.params`.

    Binds `obj_args` and `inst_args` to params by name.  `obj_args` take
    precedence, and are template-expanded with `bind_args`; `inst_args` are
    not expanded.
    """
    def get(name):
        try:
            return template_expand(obj_args[name], bind_args)
        except KeyError:
            pass
        try:
            return inst_args[name]
        except KeyError:
            pass
        raise LookupError(f"no value for param {name} of job {job.job_id}")

    return { n: get(n) for n in job.params }


#-------------------------------------------------------------------------------

class ConstantCondition(PolledCondition):
    """
    Condition with a constant value, either true or false.
    """

    def __init__(self, value):
        self.__value = bool(value)


    def __repr__(self):
        return py.format_ctor(self, self.__value)


    def bind(self, run, jobs):
        return self


    def to_jso(self):
        return super().to_jso() | {
            "value": self.__value,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            return cls(
                value=pop("value", bool),
            )


    async def check(self):
        return self.__value



