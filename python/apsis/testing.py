"""
For development/testing purposes.
"""

#-------------------------------------------------------------------------------

from   cron import *
from   cron.calendar import WeekdayCalendar

from   .program import *
from   .schedule import *
from   .types import *

#-------------------------------------------------------------------------------

JOBS = [ 
    # Job(
    #     "test-job-0",
    #     DailySchedule(
    #         "US/Eastern",
    #         WeekdayCalendar([Mon, Tue, Wed, Thu, Fri]),
    #         [Daytime(9, 30)]
    #     ),
    #     ProcessProgram(["/bin/echo", "test-job-0"]),
    # ),
    # Job(
    #     "test-job-1",
    #     DailySchedule(
    #         "US/Eastern",
    #         WeekdayCalendar([Mon, Tue, Wed, Thu, Fri]),
    #         [Daytime(16, 0)]
    #     ),
    #     ProcessProgram(["/bin/echo", "test-job-1"]),
    # ),
    # Job(
    #     "minutely",
    #     CrontabSchedule("US/Eastern"),
    #     ProcessProgram(["/bin/sleep", "5"]),
    # ),
    Job(
        "test-job-2",
        "time",
        ExplicitSchedule([ now() + 1 + i * 10 for i in range(12) ]),
        ShellCommandProgram("/Users/alex/dev/sched/jobs/test0 test-job-2"),
    ),        
]


