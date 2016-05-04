import heapq
import logging

from   .instance import Instance

#-------------------------------------------------------------------------------

# FIXME: Use cron instead.

from   datetime import datetime, timedelta
from   pytz import UTC

# **ALL** datetimes are explicitly UTC, except for I/O purposes.

def _is_datetime(time):
    return isinstance(time, datetime) and time.tzinfo == UTC


def _now():
    return UTC.localize(datetime.utcnow())


def _future(interval):
    return _now() + timedelta(0, seconds=interval)


#-------------------------------------------------------------------------------

class Scheduler:

    def __init__(self, queue, start_instance):
        self.__queue = queue
        # The queue should be entirely (UTC datetime, instance) pairs.
        assert( 
            _is_datetime(t) and isinsance(i, Instance)
            for t, i in self.__queue )

        self.__start_instance = start_instance


    @property
    def queue(self):
        return self.__queue


    def run1(self, now=None):
        """
        Schedules all jobs currently due to execute.
        """
        if now is None:
            now = _now()

        queue = self.__queue
        while len(queue) > 0 and queue[0][0] <= now:
            _, instance = heapq.heappop(queue)
            logging.debug(
                "scheduler starting instance: {}".format(instance.id))
            self.__start_instance(instance)



#-------------------------------------------------------------------------------

def schedule_instance_at(queue, instance, time):
    """
    Schedules an instance to run at `time`.
    """
    assert _is_datetime(time)
    heapq.heappush(queue, (time, instance))


def schedule_instance_in(queue, instance, delay):
    """
    Schedules an instance to run in `delay` seconds from now.
    """
    schedule_instance_at(queue, instance, _future(delay))


