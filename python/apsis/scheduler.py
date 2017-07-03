import asyncio
from   cron import *
import heapq
from   itertools import takewhile
import logging

from   .job import Instance
from   .lib import *

log = logging.getLogger("scheduler")

#-------------------------------------------------------------------------------

class Docket:
    """
    Job instances waiting to be run.
    """

    def __init__(self, time: Time):
        time = Time(time)
        self.__start    = time
        self.__stop     = time
        self.__insts    = []


    def __len__(self):
        return len(self.__insts)


    @property
    def interval(self):
        return Interval(self.__start, self.__stop)


    @property
    def next_sched_time(self):
        """
        The time of the next scheduled instance.
        """
        if len(self.__insts) > 0:
            return self.__insts[0][0]
        else:
            raise RuntimeError("no scheduled insts")


    def push(self, insts, interval):
        start, stop = interval
        assert start == self.__stop
        for inst in insts:
            assert inst.time in interval
            log.info("pushing: ({}) {}".format(inst.time, inst.id))
            heapq.heappush(self.__insts, (inst.time, inst))
        self.__stop = stop


    def pop(self, interval):
        start, stop = interval
        assert start == self.__start
        assert stop <= self.__stop

        insts = []
        while len(self.__insts) > 0 and self.__insts[0][0] < stop:
            inst_time, inst = heapq.heappop(self.__insts)
            log.info("popping: ({}) {}".format(inst_time, inst.id))
            insts.append(inst)
        self.__start = stop
        return insts



def get_schedule_insts(jobs, times: Interval):
    """
    Generates instances scheduled in interval `times`.
    """
    start, stop = times
    for job in jobs:
        for sched_time in takewhile(lambda t: t < stop, job.schedule(start)):
            inst_id = job.id + "-" + str(sched_time)
            yield Instance(inst_id, job, sched_time)


def schedule_insts(docket, jobs, time: Time):
    """
    Schedules instances of `jobs` until `time`.
    """
    time = Time(time)
    if time <= docket.interval.stop:
        # Nothing to do.
        return

    interval = Interval(docket.interval.stop, time)
    insts = get_schedule_insts(jobs, interval)
    docket.push(insts, interval)


def extract_current_insts(docket, time: Time):
    """
    Removes and returns current insts as of `time`.
    """
    time = Time(time)
    assert docket.interval.start <= time <= docket.interval.stop
    interval = Interval(docket.interval.start, time)

    return docket.pop(interval)


#-------------------------------------------------------------------------------

def run_current(docket, time):
    """
    Runs jobs in `docket` that are current at `time`.
    """
    # FIXME: Check if the docket is behind.
    insts = extract_current_insts(docket, time)
    for inst in insts:
        # FIXME: Actually run jobs.
        inst.job.program(inst)


def docket_handler(docket):
    """
    Runs jobs in `docket` currently handled, and rescheduled the handler.
    """
    # Assume (without proof?) that we're handling this handle.
    docket.handle = None

    time = now()

    # Run currently-scheduled jobs.
    run_current(docket, time)

    if len(docket) > 0:
        # Schedule the next call to this function.
        event_loop = asyncio.get_event_loop()

        next_time = docket.next_sched_time
        delay = next_time - time
        log.info("docket_handler scheduled in: {:.2f} s".format(delay))
        # Store the callback handle and the time at which it is scheduled.
        docket.handle = event_loop.call_later(delay, docket_handler, docket)
        docket.handle_time = next_time


