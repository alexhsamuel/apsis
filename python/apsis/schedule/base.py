from   dataclasses import dataclass
import ora

from   apsis.lib.json import TypedJso, check_schema

#-------------------------------------------------------------------------------

@dataclass(kw_only=True, order=True)
class DaytimeSpec:
    """
    The specification of a daytime in a schedule.

    The date and time zone are not encapsulated; these are elsewhere in the
    schedule.
    """

    cal_shift   : int = 0
    date_shift  : int = 0
    daytime     : ora.Daytime

    def __str__(self):
        return (
            format(self.daytime, "%C")
            + ("" if self.cal_shift == 0 else f" {self.cal_shift:+d} cal days")
            + ("" if self.date_shift == 0 else f" {self.date_shift:+d} days")
        )


    @classmethod
    def ensure(cls, obj):
        if isinstance(obj, cls):
            return obj

        try:
            daytime = ora.Daytime(obj)
        except (TypeError, ValueError):
            pass
        else:
            return cls(daytime=daytime)

        raise TypeError(f"not a {cls.__name__}: {obj!r}")


    def get_start_date(self, time, tz, cal):
        date, _ = time @ tz
        date -= self.date_shift
        if date not in cal:
            date = cal.after(date)
        date = cal.shift(date, -self.cal_shift)
        return date


    def to_local(self, date, tz, cal):
        """
        Combines this daytime spec with `date` to produce a time.

        :raise ora.NonexistentDateDaytime:
          The localized time doesn't exist, because it lands in a DST
          transition.
        """
        date = cal.shift(date, self.cal_shift) + self.date_shift
        return (date, self.daytime) @ tz


    def to_jso(self):
        if self.date_shift == 0 and self.cal_shift == 0:
            # Simple form: just a daytime.
            return str(self.daytime)
        else:
            return {
                "daytime"   : str(self.daytime),
                "date_shift": self.date_shift,
                "cal_shift" : self.cal_shift,
            }


    @classmethod
    def from_jso(cls, jso):
        if isinstance(jso, str):
            # Simple form: just a daytime.
            daytime = ora.Daytime(jso)
            return cls(daytime)

        with check_schema(jso) as pop:
            daytime     = pop("daytime", ora.Daytime)
            date_shift  = pop("date_shift", int, default=0)
            cal_shift   = pop("cal_shift", int, default=0)
            return cls(
                daytime=daytime, date_shift=date_shift, cal_shift=cal_shift)



#-------------------------------------------------------------------------------

class Schedule(TypedJso):

    TYPE_NAMES = TypedJso.TypeNames()

    def __init__(self, *, enabled=True):
        self.enabled = bool(enabled)


    def __call__(self, start: ora.Time):
        raise NotImplementedError



