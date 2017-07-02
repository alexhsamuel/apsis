"""
For development/testing purposes.
"""

#-------------------------------------------------------------------------------

from   cron import *
from   cron.calendar import WeekdayCalendar

from   .job import *
from   .schedule import *

#-------------------------------------------------------------------------------

JOBS = [ 
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


