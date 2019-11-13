import ora
from   ora import Date, Time, Daytime, UTC

import apsis.schedule

#-------------------------------------------------------------------------------

def test_daily_schedule_shift():
    z = "America/New_York"
    sched = apsis.schedule.DailySchedule(
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
    sched = apsis.schedule.IntervalSchedule(3600, {}, phase=900)

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
    sched = apsis.schedule.IntervalSchedule(600, args, phase=120)
    start = (date, Daytime(7, 33)) @ UTC
    times = iter(sched(start))
    assert next(times) == ((date, Daytime(7, 42)) @ UTC, args)
    assert next(times) == ((date, Daytime(7, 52)) @ UTC, args)
    assert next(times) == ((date, Daytime(8,  2)) @ UTC, args)
    assert next(times) == ((date, Daytime(8, 12)) @ UTC, args)


def test_interval_schedule_jitter():
    date = Date(2019, 11, 13)

    # Every hour on the half-hour with a 15 min jitter.
    sched = apsis.schedule.IntervalSchedule(3600, {}, phase=1800, jitter=900)
    start = (date, Daytime(7, 52)) @ UTC
    times = iter(sched(start))

    t0 = (date, Daytime(8, 30)) @ UTC
    offs = [ next(times)[0] - t0 - i * 3600 for i in range(10000) ]
    assert all( 0 <= o < 900 for o in offs )
    # Statistically likely:
    assert 0 <= min(offs) < 10
    assert 890 < max(offs) < 900



