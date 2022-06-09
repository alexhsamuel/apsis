import logging
import ora

from   apsis.lib.json import check_schema
from   .base import Schedule

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# Could be helpful for the start to be <0 and the stop to be >=24, to make
# overnight intervals easier to express.

class DailyIntervalSchedule(Schedule):

    def __init__(
            self, tz, calendar, start, stop, interval, args, *,
            enabled=True
    ):
        super().__init__(enabled=enabled)
        self.tz         = ora.TimeZone(tz)
        self.calendar   = calendar
        self.start      = ora.Daytime(start)
        self.stop       = ora.Daytime(stop)
        self.interval   = float(interval)
        if not (0 < self.interval < 86400):
            raise ValueError(f"invalid interval: {self.interval}")
        self.args       = { str(k): str(v) for k, v in args.items() }


    def __str__(self):
        res = (
            f"{self.calendar} "
            f"every {self.interval} sec "
            f"from {self.start:%C} to {self.stop:%C} {self.tz}"
        )
        if len(self.args) > 0:
            args = ", ".join( f"{k}={v}" for k, v in self.args.items() )
            res = "(" + args + ") " + res
        return res


    def __call__(self, start: ora.Time):
        """
        Generates scheduled times starting not before `start`.
        """
        start = ora.Time(start)
        date, _ = start @ self.tz
        date = self.calendar.after(date)

        while True:
            daytime = self.start
            while daytime < self.stop:
                try:
                    time = (date, daytime) @ self.tz
                except ora.NonexistentDateDaytime:
                    # Landed on a DST transformation.
                    log.warning(
                        "skipping nonexistent schedule time "
                        f"{date} {daytime} {self.tz}"
                    )
                    continue
                if start <= time:
                    yield time, {
                        "date"      : str(date),
                        "time"      : str(time),
                        "daytime"   : str(daytime),
                        "calendar"  : str(self.calendar),
                        "tz"        : str(self.tz),
                    }
                next_daytime = daytime + self.interval
                if next_daytime < daytime:
                    # We wrapped around.
                    break
                daytime = next_daytime

            date = self.calendar.after(date + 1)


    def to_jso(self):
        return {
            **super().to_jso(),
            "tz"        : str(self.tz),
            "calendar"  : repr(self.calendar),
            "start"     : str(self.start),
            "stop"      : str(self.stop),
            "interval"  : self.interval,
            "args"      : self.args,
            "enabled"   : self.enabled,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            tz          = pop("tz", ora.TimeZone)
            calendar    = ora.get_calendar(pop("calendar", default="all"))
            start       = pop("start", ora.Daytime)
            stop        = pop("stop", ora.Daytime)
            interval    = pop("interval", int)
            args        = pop("args", default={})
            enabled     = pop("enabled", bool, default=True)
        return cls(
            tz, calendar, start, stop, interval, args,
            enabled=enabled,
        )



