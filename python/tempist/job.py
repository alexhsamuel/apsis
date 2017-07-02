from    aslib.py import format_ctor

#-------------------------------------------------------------------------------

class Job:

    def __init__(self, id, schedule):
        self.__id = str(id)
        self.__schedule = schedule


    @property
    def id(self):
        return self.__id


    @property
    def schedule(self):
        return self.__schedule



class Instance:

    def __init__(self, id, job_id, time):
        self.__id       = id
        self.__job_id   = job_id
        self.__time     = time


    def __repr__(self):
        return format_ctor(self, self.__id, self.__job_id, self.__time)


    @property
    def id(self):
        return self.__id


    @property
    def time(self):
        return self.__time



#-------------------------------------------------------------------------------
# FIXME: For development/testing only.

from   cron.calendar import WeekdayCalendar

from   .schedule import *


TEST_JOBS = [ 
    Job(
        "test-job-0",
        Schedule(
            "US/Eastern",
            WeekdayCalendar([Mon, Tue, Wed, Thu, Fri]),
            [Daytime(9, 30)]
        )
    ),
    Job(
        "test-job-1",
        Schedule(
            "US/Eastern",
            WeekdayCalendar([Mon, Tue, Wed, Thu, Fri]),
            [Daytime(16, 0)]
        )
    ),
    Job(
        "minutely",
        CrontabSchedule("US/Eastern"),
    ),
]


