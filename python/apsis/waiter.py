import logging

from   .lib.json import Typed, no_unexpected_keys
from   .lib.py import or_none
from   .runs import Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class MaxRunningPreco:

    def __init__(self, job_id, args, count):
        self.__job_id = job_id
        self.__args = args
        self.__count = count


    def to_jso(self):
        jso = {
            "count": self.__count,
        }
        if self.__job_id is not None:
            jso["job_id"] = self.__job_id
        if self.__args is not None:
            jso["args"] = self.__args
        return jso


    @classmethod
    def from_jso(Class, jso):
        return Class(
            jso.pop("job_id", None),
            jso.pop("args", None),
            jso.pop("count")
        )


    def bind(self, job_id, args):
        job_id  = or_none(self.__job_id, job_id)
        args    = or_none(self.__args, args)
        count   = int(self.__count)
        return type(self)(job_id, args, count)


    def check(self, runs):
        _, running = runs.query(job_id=self.__job_id, state=Run.STATE.running)
        count = len(list(running))
        return count < self.__count



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

        self.__waiting = {}


    async def start(self, run):
        log.info(f"no conditions; starting: {run}")
        await self.__start(run)



