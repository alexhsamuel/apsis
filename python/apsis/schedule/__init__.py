from   .base import Schedule
from   .daily import DailySchedule
from   .explicit import ExplicitSchedule
from   .interval import IntervalSchedule

#-------------------------------------------------------------------------------

Schedule.TYPE_NAMES.set(DailySchedule, "daily")
Schedule.TYPE_NAMES.set(ExplicitSchedule, "explicit")
Schedule.TYPE_NAMES.set(IntervalSchedule, "interval")

