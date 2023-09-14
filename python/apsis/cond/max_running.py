import logging

from   apsis.lib.py import format_ctor
from   apsis.runs import Run, get_bind_args, template_expand
from   .base import RunStoreCondition

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class MaxRunning(RunStoreCondition):

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
        msg = f"max {self.__count} running"
        if self.__job_id is not None:
            msg += f" {self.__job_id}"
            if self.__args is not None:
                args = " ".join( f"{k}={v}" for k, v in self.__args.items() )
                msg += f"({args})"
        return msg


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


    def check(self, run_store):
        max_count = int(self.__count)
        # Count running jobs.
        _, running = run_store.query(
            job_id  =self.__job_id,
            args    =self.__args,
            state   =(Run.STATE.starting, Run.STATE.running),
        )
        count = len(list(running))
        log.debug(f"found {count} running")
        return count < max_count


    async def wait(self, run_store):
        # Set up a live query for any changes to a run with the relevant job ID
        # and args.
        with run_store.query_live(
                job_id  =self.__job_id,
                args    =self.__args,
        ) as queue:
            while not self.check(run_store):
                # Wait until a relevant run transitions, then check again.
                _ = await queue.get()

        return True



