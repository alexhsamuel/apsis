import ora

from   apsis.lib.json import check_schema
from   apsis.lib.py import format_ctor
from   .base import Schedule

#-------------------------------------------------------------------------------

class IntervalSchedule(Schedule):

    def __init__(self, interval, args, *, enabled=True, phase=0.0):
        super().__init__(enabled=enabled)
        self.interval   = float(interval)
        self.phase      = float(phase)
        self.args       = { str(k): str(v) for k, v in args.items() }

        assert 0 <= self.phase < self.interval


    def __repr__(self):
        return format_ctor(self, self.interval, self.args)


    def __str__(self):
        res = f"every {self.interval} sec"
        if len(self.args) > 0:
            args = ", ".join( f"{k}={v}" for k, v in self.args.items() )
            res = "(" + args + ") " + res
        return res


    def __call__(self, start: ora.Time):
        # Round to the next interval.
        start -= self.phase
        off = start - ora.Time.EPOCH
        time = (
            start if off % self.interval == 0
            else ora.Time.EPOCH + (off // self.interval + 1) * self.interval
        ) + self.phase

        while True:
            yield time, {"time": str(time), **self.args}
            time += self.interval


    def to_jso(self):
        return {
            **super().to_jso(),
            "enabled"   : self.enabled,
            "interval"  : self.interval,
            "phase"     : self.phase,
            "args"      : self.args,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            enabled     = pop("enabled", bool, default=True)
            interval    = pop("interval", int)
            phase       = pop("phase", float, 0)
            assert 0 <= phase < interval, "phase not between 0 and interval"
            args        = pop("args", default={})
        return cls(interval, args, enabled=enabled, phase=phase)



