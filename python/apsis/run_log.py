import logging
from   ora import now
import sys

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class RunLog:
    """
    Log of a run's activity, for human consumption.
    """

    def __init__(self, run_log_db):
        self.__run_log_db = run_log_db


    def record(self, run, message, *, timestamp=None):
        """
        Records a timestamped run log record for `run`.

        :param timestamp:
          The time of the event; current time if none.
        """
        message = str(message)
        timestamp = now() if timestamp is None else timestamp

        db = self.__run_log_db
        if run.expected:
            db.cache(run.run_id, timestamp, message)
        else:
            db.insert(run.run_id, timestamp, message)


    def info(self, run, message, *, timestamp=None):
        """
        Records a run log record and logs at level INFO.
        """
        log.debug(f"run {run.run_id}: {message}")
        self.record(run, message, timestamp=timestamp)


    def error(self, run, message, *, timestamp=None):
        """
        Records a run log record and logs at level ERROR.
        """
        log.error(f"run {run.run_id}: {message}")
        self.record(run, f"error: {message}", timestamp=timestamp)


    def exc(self, run, message=None, *, timestamp=None):
        """
        Records an exception for `run` and logs at level ERROR.
        """
        _, exc_msg, _ = sys.exc_info()

        log_msg = f"run {run.run_id}"
        if message is not None:
            log_msg += ": " + str(message)
        log_msg += ": " + str(exc_msg)
        log.error(log_msg, exc_info=True)

        self.record(run, f"error: {exc_msg}", timestamp=timestamp)


