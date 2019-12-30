import logging

from   apsis.lib.py import format_ctor
from   apsis.runs import Run, get_bind_args, template_expand
from   .base import Condition

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class MaxRunning(Condition):

    def __init__(self, count, job_id=None, args=None):
        """
        :param job_id:
          Job ID of runs to count.  If none, bound to the job ID of the 
          owning instance.
        :param args:
          Args to match.  If none, the bound to the args of the owning instance.
        """
        self.__count = count
        self.__job_id = job_id
        self.__args = args


    def __repr__(self):
        return format_ctor(
            self, self.__count, job_id=self.__job_id, args=self.__args)


    def __str__(self):
        args = (
            None if self.__args is None
            else " ".join( f"{k}={v}" for k, v in self.__args.items() )
        )
        return f"max {self.__count} running {self.__job_id}({args})"


    def to_jso(self):
        return {
            **super().to_jso(),
            "count" : self.__count,
            "job_id": self.__job_id,
             "args" : self.__args,
        }


    @classmethod
    def from_jso(cls, jso):
        return cls(
            jso.pop("count", "1"),
            jso.pop("job_id", None),
            jso.pop("args", None),
        )


    def bind(self, run, jobs):
        bind_args = get_bind_args(run)
        count = template_expand(self.__count, bind_args)
        job_id = run.inst.job_id if self.__job_id is None else self.__job_id
        # FIXME: Support self.__args not none.  Template-expand them, add in
        # inst.args, and bind to job args.
        if self.__args is not None:
            raise NotImplementedError()
        return type(self)(count, job_id, run.inst.args)


    def check_runs(self, run_store):
        max_count = int(self.__count)

        # FIXME: Support query by args.
        _, running = run_store.query(
            job_id=self.__job_id, 
            state=Run.STATE.running,
        )
        for name, val in self.__args.items():
            running = ( r for r in running if r.inst.args.get(name) == val )
        count = len(list(running))
        log.debug(f"count matching {self.__job_id} {self.__args}: {count}")
        return count < max_count



