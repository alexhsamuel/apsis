import ora
from   ora import Date, Time, Daytime, UTC

from   apsis.schedule import DailySchedule, IntervalSchedule

#-------------------------------------------------------------------------------

def test_daily_schedule_shift():
    z = "America/New_York"
    sched = DailySchedule(
        z,
        ora.get_calendar("Mon,Wed-Fri"),
        ["9:30:00", "16:00:00"],
        {"foo": "bar"},
        date_shift=-1,
    )

    nd = lambda t: next(sched(t))

    # Fri 00:00 -> Sun 09:30 for Mon.
    st, a = nd(Time(2019, 1, 11,  0, 0, 0, z))
    assert st == Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"
    assert a["foo"] == "bar"

    # Sat 05:00 -> Sun 09:30 for Mon.
    st, a = nd(Time(2019, 1, 12,  5, 0, 0, z))
    assert st == Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"
    assert a["foo"] == "bar"

    # Sun 09:15 -> Sun 09:30 for Mon.
    st, a = nd(Time(2019, 1, 13, 9, 15, 0, z))
    assert st == Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 09:45 -> Sun 16:00 for Mon.
    st, a = nd(Time(2019, 1, 13, 9, 45, 0, z))
    assert st == Time(2019, 1, 13, 16, 0, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 15:55 -> Sun 16:00 for Mon.
    st, a = nd(Time(2019, 1, 13, 15, 55, 0, z))
    assert st == Time(2019, 1, 13, 16, 0, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 16:02 -> Tue 09:30 for Wed.
    st, a = nd(Time(2019, 1, 13, 16, 2, 0, z))
    assert st == Time(2019, 1, 15, 9, 30, 0, z)
    assert a["date"] == "2019-01-16"

    # Mon 12:00 -> Tue 09:30 for Wed.
    st, a = nd(Time(2019, 1, 14, 0, 0, 0, z))
    assert st == Time(2019, 1, 15, 9, 30, 0, z)
    assert a["date"] == "2019-01-16"

    # Tue 09:40 -> Tue 16:00 for Wed.
    st, a = nd(Time(2019, 1, 15, 9, 40, 0, z))
    assert st == Time(2019, 1, 15, 16, 0, 0, z)
    assert a["date"] == "2019-01-16"

    # Tue 17:00 -> Wed 09:30 for Thu.
    st, a = nd(Time(2019, 1, 15, 17, 0, 0, z))
    assert st == Time(2019, 1, 16, 9, 30, 0, z)
    assert a["date"] == "2019-01-17"

    # Thu 20:00 -> Sun 09:30 for Mon.
    st, a = nd(Time(2019, 1, 17, 20, 0, 0, z))
    assert st == Time(2019, 1, 20, 9, 30, 0, z)
    assert a["date"] == "2019-01-21"


def test_interval_schedule_phase():
    # Every hour on the 15 min.
    sched = IntervalSchedule(3600, {}, phase=900)

    st, _ = next(sched(Time(2019, 11, 13, 7, 5, 0, UTC)))
    assert st == Time(2019, 11, 13, 7, 15, 0, UTC)

    st, _ = next(sched(Time(2019, 11, 13, 7, 14, 59, UTC)))
    assert st == Time(2019, 11, 13, 7, 15, 0, UTC)

    st, _ = next(sched(Time(2019, 11, 13, 7, 15, 0, UTC)))
    assert st == Time(2019, 11, 13, 7, 15, 0, UTC)

    st, _ = next(sched(Time(2019, 11, 13, 7, 25, 0, UTC)))
    assert st == Time(2019, 11, 13, 8, 15, 0, UTC)

    st, _ = next(sched(Time(2019, 11, 13, 7, 55, 0, UTC)))
    assert st == Time(2019, 11, 13, 8, 15, 0, UTC)


def test_interval_schedule_phase_repeat():
    args = {"foo": "42"}
    date = Date(2019, 11, 13)

    # Every 10 min with phase of 2 min.
    sched = IntervalSchedule(600, args, phase=120)
    start = (date, Daytime(7, 33)) @ UTC
    times = iter(sched(start))
    assert next(times) == ((date, Daytime(7, 42)) @ UTC, args)
    assert next(times) == ((date, Daytime(7, 52)) @ UTC, args)
    assert next(times) == ((date, Daytime(8,  2)) @ UTC, args)
    assert next(times) == ((date, Daytime(8, 12)) @ UTC, args)


def test_daily_schedule_eq():
    z1 = ora.TimeZone("America/New_York")

    c0 = ora.get_calendar("Mon-Fri")
    c1 = ora.get_calendar("all")

    a0 = dict(veg="tomato")
    a1 = dict(veg="eggplant")

    s0 = DailySchedule(ora.UTC, c0, ["9:30:00"], a0)
    s1 = DailySchedule(ora.UTC, c0, ["9:30:00"], a0)
    assert s0 == s1

    s2 = DailySchedule(z1, c0, ["9:30:00"], a0)
    assert s0 != s2

    s3 = DailySchedule(ora.UTC, c1, ["9:30:00"], a0)
    assert s0 != s3

    s4 = DailySchedule(ora.UTC, c0, ["9:45:00"], a0)
    assert s0 != s4

    s5 = DailySchedule(ora.UTC, c0, ["9:30:00", "16:00:00"], a0)
    assert s0 != s5

    s6 = DailySchedule(ora.UTC, c0, ["9:30:00"], a1)
    assert s0 != s6

    s7 = DailySchedule(ora.UTC, c0, ["9:30:00"], a1, date_shift=-1)
    assert s0 != s7

    s8 = DailySchedule(ora.UTC, c0, ["9:30:00"], a1, enabled=False)
    assert s0 != s8


def test_interval_schedule_eq():
    s0 = IntervalSchedule(3600, {"foo": 42})
    s1 = IntervalSchedule(3600, {"foo": 42})
    assert s0 == s1

    s2 = IntervalSchedule(1800, {"foo": 42})
    assert s0 != s2

    s3 = IntervalSchedule(3600, {"foo": 17})
    assert s0 != s3

    s4 = IntervalSchedule(3600, {"foo": 42}, enabled=False)
    assert s0 != s4

    s5 = IntervalSchedule(3600, {"foo": 42}, phase=600)
    assert s0 != s5


