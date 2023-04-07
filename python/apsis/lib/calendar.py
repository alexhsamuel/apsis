import functools
import ora.calendar

#-------------------------------------------------------------------------------

# Cache calendars.  We assume on-disk calendars don't change during the
# scheduler's lifetime.
get_calendar = functools.cache(ora.calendar.get_calendar)


