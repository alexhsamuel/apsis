import ora

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
    st, a = nd(ora.Time(2019, 1, 11,  0, 0, 0, z))
    assert st == ora.Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"
    assert a["foo"] == "bar"

    # Sat 05:00 -> Sun 09:30 for Mon.
    st, a = nd(ora.Time(2019, 1, 12,  5, 0, 0, z))
    assert st == ora.Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"
    assert a["foo"] == "bar"

    # Sun 09:15 -> Sun 09:30 for Mon.
    st, a = nd(ora.Time(2019, 1, 13, 9, 15, 0, z))
    assert st == ora.Time(2019, 1, 13, 9, 30, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 09:45 -> Sun 16:00 for Mon.
    st, a = nd(ora.Time(2019, 1, 13, 9, 45, 0, z))
    assert st == ora.Time(2019, 1, 13, 16, 0, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 15:55 -> Sun 16:00 for Mon.
    st, a = nd(ora.Time(2019, 1, 13, 15, 55, 0, z))
    assert st == ora.Time(2019, 1, 13, 16, 0, 0, z)
    assert a["date"] == "2019-01-14"

    # Sun 16:02 -> Tue 09:30 for Wed.
    st, a = nd(ora.Time(2019, 1, 13, 16, 2, 0, z))
    assert st == ora.Time(2019, 1, 15, 9, 30, 0, z)
    assert a["date"] == "2019-01-16"

    # Mon 12:00 -> Tue 09:30 for Wed.
    st, a = nd(ora.Time(2019, 1, 14, 0, 0, 0, z))
    assert st == ora.Time(2019, 1, 15, 9, 30, 0, z)
    assert a["date"] == "2019-01-16"

    # Tue 09:40 -> Tue 16:00 for Wed.
    st, a = nd(ora.Time(2019, 1, 15, 9, 40, 0, z))
    assert st == ora.Time(2019, 1, 15, 16, 0, 0, z)
    assert a["date"] == "2019-01-16"

    # Tue 17:00 -> Wed 09:30 for Thu.
    st, a = nd(ora.Time(2019, 1, 15, 17, 0, 0, z))
    assert st == ora.Time(2019, 1, 16, 9, 30, 0, z)
    assert a["date"] == "2019-01-17"

    # Thu 20:00 -> Sun 09:30 for Mon.
    st, a = nd(ora.Time(2019, 1, 17, 20, 0, 0, z))
    assert st == ora.Time(2019, 1, 20, 9, 30, 0, z)
    assert a["date"] == "2019-01-21"


