import logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Waiter:

    def __init__(self, run_db, start):
        self.__run_db = run_db
        self.__start = start

        self.__waiting = {}


    async def start(self, run):
        log.info(f"no conditions; starting: {run}")
        await self.__start(run)



