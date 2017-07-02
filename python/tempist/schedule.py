import bisect

from   cron import *

#-------------------------------------------------------------------------------

# FIXME: For demonstration only.
class Schedule:

    def __init__(self, tz, calendar, daytimes):
        self.__tz       = TimeZone(tz)
        self.__calendar = calendar
        self.__daytimes = tuple(sorted( Daytime(t) for t in daytimes ))


    def __call__(self, start):
        """
        Generates scheduled times starting not before `start`.
        """
        start = Time(start)

        local = to_local(start, self.__tz)
        if local.date in self.__calendar:
            date = local.date
            # Find the next daytime.
            for i, daytime in enumerate(self.__daytimes):
                if daytime <= local.daytime:
                    break
            else:
                # All daytimes have passed for this date.
                date = self.__calendar.shift(date, 1)
                i = 0
        else:
            # Start at the beginning of the next date.
            date = self.__calendar.next(local.date)
            i = 0

        # Now generate.
        while True:
            yield from_local((date, self.__daytimes[i]), self.__tz)
            i += 1
            if i == len(self.__daytimes):
                # On to the next day.
                date = self.__calendar.shift(date, 1)
                i = 0



class ListSchedule:

    def __init__(self, times):
        self.__times = tuple(sorted( Daytime(t) for t in times ))


    def __call__(self, start):
        start = Time(start)
        i = bisect.bisect_left(self.__times, start)
        return iter(self.__times[i :])



