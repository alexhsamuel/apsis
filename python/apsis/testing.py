"""
For development/testing purposes.
"""

#-------------------------------------------------------------------------------

import math
from   ora import now
# from   ora.calendar import WeekdayCalendar
import random

from   .program import AgentShellProgram
from   .schedule import ExplicitSchedule
from   .types import Job

#-------------------------------------------------------------------------------

time = now()
time = time.MIN + math.ceil(time - time.MIN)

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
        "hot-test",
        "time",
        ExplicitSchedule([ time + 1 + i * 10 for i in range(12) ]),
        AgentShellProgram("$HOME/dev/apsis/jobs/test0 hot-test"),
    ),        
]


def get_test_job(num):
    start = now()
    start = start.MIN + math.ceil(start - start.MIN)
    times = [ start + random.randint(-60, 900) for _ in range(num) ]
    return Job(
        "hot",
        "time",
        ExplicitSchedule(times),
        AgentShellProgram("$HOME/dev/apsis/jobs/test0 hot-test"),
    )


