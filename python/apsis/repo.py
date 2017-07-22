"""
Job repository.
"""

#-------------------------------------------------------------------------------

import cron
import cron.calendar
import os
from   pathlib import Path
import ruamel_yaml as yaml

from   . import program
from   .job import Job
from   .schedule import DailySchedule

#-------------------------------------------------------------------------------

# FIXME: Move to cron.

def weekday_range(start, end):
    return [ 
        cron.Weekday(w) 
        for w in range(int(start), int(end) + (7 if end < start else 0) + 1)
    ]


def get_calendar(name):
    # FIXME: Support named calendars, loaded from somewhere.
    # FIXME: Handle errors sensibly.
    if name == "all":
        return cron.calendar.AllCalendar()
    elif "-" in name:
        start, end = name.split("-")
        start = cron.Weekday[start]
        end = cron.Weekday[end]
        return cron.calendar.WeekdayCalendar(weekday_range(start, end))
    else:
        return sorted(set( cron.Weekday[w.strip()] for w in name.split(",") ))


#-------------------------------------------------------------------------------

class JobSpecificationError(Exception):

    pass



def jso_to_schedule(jso):
    args = jso.get("args", {})

    try:
        tz = jso["tz"]
    except KeyError:
        raise JobSpecificationError("missing time zone")
    tz = cron.TimeZone(tz)

    calendar = get_calendar(jso.get("calendar", "all"))

    try:
        daytimes = jso["daytime"]
    except KeyError:
        raise JobSpecificationError("missing daytime")
    daytimes = [daytimes] if isinstance(daytimes, str) else daytimes
    daytimes = [ cron.Daytime(d) for d in daytimes ]

    return DailySchedule(tz, calendar, daytimes, args)


def jso_to_program(jso):
    if isinstance(jso, str):
        return program.ShellCommandProgram(jso)
    elif isinstance(jos, list):
        return program.ProcessProgram(jso)
    else:
        # FIXME: Support something reasonable here.
        raise JobSpecificationError("bad program")


def jso_to_job(jso, job_id):
    params = jso.get("params", "date")
    params = [params] if isinstance(params, str) else params

    try:
        schedules = jso["schedule"]
    except KeyError:
        raise JobSpecificationError("missing schedule")
    schedules = [schedules] if isinstance(schedules, dict) else schedules
    schedules = [ jso_to_schedule(s) for s in schedules ]

    try:
        program = jso["program"]
    except KeyError:
        raise JobSpecificationError("missing program")
    program = jso_to_program(program)

    return Job(job_id, params, schedules, program)


def load_yaml(file, job_id):
    jso = yaml.load(file)
    return jso_to_job(jso, job_id)


def load_yaml_files(dir_path):
    dir_path = Path(dir_path)
    for dir, _, names in os.walk(dir_path):
        dir = Path(dir)
        paths = ( dir / n for n in names )
        paths = ( p for p in paths if p.suffix == ".yaml" )
        for path in paths:
            name = path.with_suffix("").relative_to(dir_path)
            with open(path) as file:
                yield load_yaml(file, name)


