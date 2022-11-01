import logging

from   apsis.lib import py
from   apsis.lib.json import check_schema
from   apsis.runs import Instance, to_state
from   .base import Condition

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class SkipDuplicate(Condition):
    """
    Transitions a run if another run with the same job_id and args exists.
    """

    DEFAULT_IF_STATES = ("waiting", "starting", "running")

    def __init__(
            self, *,
            if_states   =DEFAULT_IF_STATES,
            target      ="skipped",
            instance    =None,
    ):
        """
        :param if_states:
          Run states to consider when looking for duplicates.
        :param target:
          The state to transition this run to.
        """
        self.__if_states    = [ to_state(s) for s in py.iterize(if_states) ]
        self.__target       = to_state(target)
        self.__instance     = instance


    def __repr__(self):
        return py.format_ctor(
            self, if_states=self.__if_states, target=self.__target,
            instance=self.__instance,
        )


    def __str__(self):
        inst = "" if self.__instance is None else f"{self.__instance} is"
        states = ", ".join( s.name for s in self.__if_states )
        return f"transition to {self.__target.name} if {inst} {states}"


    def to_jso(self):
        jso = {
            **super().to_jso(),
            "if_states" : [ s.name for s in self.__if_states ],
            "target"    : self.__target.name,
        }
        if self.__instance is not None:
            jso["instance"] = self.__instance.to_jso()
        return jso


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            return cls(
                if_states   =pop("if_states", default=cls.DEFAULT_IF_STATES),
                target      =pop("target", default="skipped"),
                instance    =pop("instance", Instance.from_jso, None),
            )


    def bind(self, run, jobs):
        assert self.__instance is None, "already bound"
        return type(self)(
            if_states   =self.__if_states,
            target      =self.__target,
            instance    =run.inst,
        )


    def check_runs(self, run_store):
        _, runs = run_store.query(
            job_id=self.__instance.job_id, args=self.__instance.args,
            state=self.__if_states,
        )
        # But exclude ourselvbe
        runs = list(runs)
        log.debug(f"runs {self.__instance} {self.__if_states}: {len(runs)}")
        return (
            self.Transition(
                self.__target,
                f"transitioning to {self.__target.name} due to "
                f"{runs[0].run_id} {runs[0].state.name}"
            ) if len(runs) > 0
            else True
        )


