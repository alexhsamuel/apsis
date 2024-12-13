import ora

from   apsis.runs import Instance, Run
from   apsis.states import State
from   apsis.stop import StopSchedule

#-------------------------------------------------------------------------------

RUN = Run(Instance("test job", {}))
RUN.state = State.running
RUN.times.update({
    "scheduled" : ora.Time("2024-12-12T23:00:00Z"),
    "schedule"  : ora.Time("2024-12-13T12:00:00Z"),
    "waiting"   : ora.Time("2024-12-13T12:00:01Z"),
    "starting"  : ora.Time("2024-12-13T12:10:00Z"),
    "running"   : ora.Time("2024-12-13T12:10:05Z"),
})

# A run missing some of the `times` entries.
AD_HOC_RUN = Run(Instance("test job", {}))
AD_HOC_RUN.state = State.success
AD_HOC_RUN.times.update({
    "starting"  : ora.Time("2024-12-13T12:10:23Z"),
    "running"   : ora.Time("2024-12-13T12:11:05Z"),
})


def test_stop_duration_schedule():
    sched = StopSchedule.from_jso({
        "type": "duration",
        "duration": "1h",
    })
    assert sched == StopSchedule.from_jso(sched.to_jso())
    assert "3600" in repr(sched)
    assert "3600" in str(sched)
    jso = sched.to_jso()
    assert jso["duration"] == 3600
    assert sched(RUN) == ora.Time("2024-12-13T13:00:00Z")
    assert sched(AD_HOC_RUN) == ora.Time("2024-12-13T13:10:23Z")

    sched = StopSchedule.from_jso({
        "type": "duration",
        "duration": "1h",
        "after": "running",
    })
    assert sched == StopSchedule.from_jso(sched.to_jso())
    jso = sched.to_jso()
    assert jso["after"] == "running"
    assert sched(RUN) == ora.Time("2024-12-13T13:10:05Z")
    assert sched(AD_HOC_RUN) == ora.Time("2024-12-13T13:11:05Z")


def test_stop_daytime_schedule():
    sched = StopSchedule.from_jso({
        "type": "daytime",
        "daytime": "16:00:00",
        "tz": "UTC",
    })
    assert sched == StopSchedule.from_jso(sched.to_jso())
    assert "UTC" in repr(sched)
    assert "16:00:00" in str(sched)
    jso = sched.to_jso()
    assert jso["daytime"] == "16:00:00"
    assert jso["tz"] == "UTC"
    assert sched(RUN) == ora.Time("2024-12-13T16:00:00Z")
    assert sched(AD_HOC_RUN) == ora.Time("2024-12-13T16:00:00Z")

    sched = StopSchedule.from_jso({
        "type": "daytime",
        "daytime": "16:00:00",
        "tz": "Asia/Tokyo",
        "after": "waiting",
    })
    assert sched == StopSchedule.from_jso(sched.to_jso())
    assert "Asia/Tokyo" in repr(sched)
    jso = sched.to_jso()
    assert jso["tz"] == "Asia/Tokyo"
    assert jso["after"] == "waiting"
    # Next day in Tokyo.
    assert sched(RUN) == ora.Time("2024-12-14T07:00:00Z")
    assert sched(AD_HOC_RUN) == ora.Time("2024-12-14T07:00:00Z")


