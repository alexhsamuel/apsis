import logging

from   .lib.json import Typed, no_unexpected_keys
from   .runs import Run, Instance, template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class MaxRunningPreco:

    def __init__(self, count, inst):
        self.__count = count
        self.__inst = inst


    def to_jso(self):
        jso = {
            "count": self.__count,
        }
        if self.__inst is not None:
            jso.update({
                "job_id": self.__inst.job_id,
                "args": self.__inst.args,
            })
        return jso


    @classmethod
    def from_jso(Class, jso):
        count = str(jso.pop("count"))
        try:
            inst = Instance(jso.pop("job_id"), jso.pop("args"))
        except KeyError:
            inst = None
        return Class(count, inst)


    def bind(self, args, inst):
        count = template_expand(self.__count, args)
        return type(self)(count, inst)


    def check_runs(self, runs):
        # FIXME: Support query by args.
        _, running = runs.query(
            job_id=self.__inst.job_id, 
            state=Run.STATE.running,
        )
        running = [ r for r in running if r.args == self.__inst.args ]
        return len(running) < self.__count



TYPES = Typed({
    "max_running"       : MaxRunningPreco,
})

def preco_from_jso(jso):
    with no_unexpected_keys(jso):
        return TYPES.from_jso(jso)


preco_to_jso = TYPES.to_jso

#-------------------------------------------------------------------------------

class Waiter:

    def __init__(self, run_db, start):
        self.__run_db = run_db
        self.__start = start

        self.__run_waiting = {}


    async def start(self, run):
        log.info(f"no conditions; starting: {run}")
        await self.__start(run)



