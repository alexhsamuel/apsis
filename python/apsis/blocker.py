import logging

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class Blocker:

    def __init__(self, run_db, start):
        self.__run_db = run_db
        self.__start = start

        self.__blocked = {}


    async def start(self, run):
        log.info(f"no conditions; starting: {run}")
        await self.__start(run)



