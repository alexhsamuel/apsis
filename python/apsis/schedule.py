import bisect
from   cron import *
from   functools import partial

from   . import lib
from   .crontab import CrontabSchedule

#-------------------------------------------------------------------------------
# FIXME: Elsewhere

# FIXME: This is horrendous.
def calendar_from_jso(jso):
    import cron.calendar
    type_name = jso.pop("$type")
    class_ = getattr(cron.calendar, type_name)
    return class_(**jso)


#-------------------------------------------------------------------------------

class DailySchedule:

    def __init__(self, tz, calendar, daytimes, args):
        self.tz         = TimeZone(tz)
        self.calendar   = calendar
        self.daytimes   = tuple(sorted( Daytime(t) for t in daytimes ))
        self.args       = { str(k): str(v) for k, v in args.items() }


    def __str__(self):
        return "at {} on {} in {} for {}".format(
            " ".join( format(y, "%H:%M:%S") for y in self.daytimes ),
            self.calendar,
            self.tz,
            " ".join( "{}={}".format(k, v) for k, v in self.args.items() )
        )


    def __call__(self, start):
        """
        Generates scheduled times starting not before `start`.
        """
        start = Time(start)

        local = to_local(start, self.tz)
        if local.date in self.calendar:
            date = local.date
            # Find the next daytime.
            for i, daytime in enumerate(self.daytimes):
                if local.daytime <= daytime:
                    break
            else:
                # All daytimes have passed for this date.
                date = self.calendar.shift(date, 1)
                i = 0
        else:
            # Start at the beginning of the next date.
            date = self.calendar.next(local.date)
            i = 0

        # Now generate.
        while True:
            yield from_local((date, self.daytimes[i]), self.tz)
            i += 1
            if i == len(self.daytimes):
                # On to the next day.
                date = self.calendar.shift(date, 1)
                i = 0


    def bind_args(self, params, sched_time):
        args = dict(self.args)

        # Bind temporal params from the schedule time.
        if "time" in params:
            # FIXME: Localize to TZ?  Or not?
            args["time"] = lib.format_time(sched_time)
        if "date" in params:
            args["date"] = str((sched_time @ self.tz).date)

        return args


    def to_jso(self):
        return {
            "tz"        : str(self.tz),
            "calendar"  : repr(self.calendar),  # FIXME
            "daytimes"  : [ str(y) for y in self.daytimes ],
            "args"      : self.args,
        }


    @classmethod
    def from_jso(class_, jso):
        return class_(
            jso["tz"], 
            calendar_from_jso(jso["calendar"]),
            jso["daytimes"],
            jso["args"],
        )



class ExplicitSchedule:

    def __init__(self, times):
        self.__times = tuple(sorted( Time(t) for t in times ))


    def __str__(self):
        return ",".join( str(t) for t in self.__times )


    def __call__(self, start):
        start = Time(start)
        i = bisect.bisect_left(self.__times, start)
        return iter(self.__times[i :])


    def bind_args(self, params, sched_time):
        args = {}
        if "time" in params:
            args["time"] = lib.format_time(sched_time)
        return args


    def to_jso(self):
        return {
            "times" : [ str(t) for t in self.__times ],
        }



#-------------------------------------------------------------------------------

TYPES = (
    CrontabSchedule,
    DailySchedule,
    ExplicitSchedule,
)

from_jso    = partial(lib.from_jso, types=TYPES)

