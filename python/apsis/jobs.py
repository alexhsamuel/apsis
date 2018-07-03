import ora
import ora.calendar
import os
from   pathlib import Path
import ruamel_yaml as yaml

from   . import program
from   .lib.py import tupleize
from   .schedule import DailySchedule

#-------------------------------------------------------------------------------

class Reruns:
    """
    :ivar count:
      Maximum number of reruns; 0 for no reruns.
    :ivar delay:
      Delay after failure before rerun.
    :ivar max_delay:
      Maximum delay after schedule time for starting a rerun.  If this delay
      has elapsed, no further reruns are attempted.
    """

    def __init__(self, count=0, delay=0, max_delay=None):
        self.count      = int(count)
        self.delay      = float(delay)
        self.max_delay  = None if max_delay is None else float(max_delay)



class Job:

    def __init__(self, job_id, params, schedules, program, reruns=Reruns()):
        """
        :param schedules:
          A sequence of `Schedule, args` pairs, where `args` is an arguments
          dict.
        """
        self.job_id     = str(job_id)
        self.params     = frozenset( str(p) for p in tupleize(params) )
        self.schedules  = tupleize(schedules)
        self.program    = program
        self.reruns     = reruns



#-------------------------------------------------------------------------------

# FIXME: Move to ora.

def weekday_range(start, end):
    return [ 
        ora.Weekday(w) 
        for w in range(int(start), int(end) + (7 if end < start else 0) + 1)
    ]


def get_calendar(name):
    # FIXME: Support named calendars, loaded from somewhere.
    # FIXME: Handle errors sensibly.
    if name == "all":
        return ora.calendar.AllCalendar()
    elif "-" in name:
        start, end = name.split("-")
        start = ora.Weekday[start]
        end = ora.Weekday[end]
        return ora.calendar.WeekdayCalendar(weekday_range(start, end))
    else:
        return sorted(set( ora.Weekday[w.strip()] for w in name.split(",") ))


#-------------------------------------------------------------------------------

class JobSpecificationError(Exception):

    pass



def jso_to_schedule(jso):
    args = jso.get("args", {})

    try:
        tz = jso["tz"]
    except KeyError:
        raise JobSpecificationError("missing time zone")
    tz = ora.TimeZone(tz)

    calendar = get_calendar(jso.get("calendar", "all"))

    try:
        daytimes = jso["daytime"]
    except KeyError:
        raise JobSpecificationError("missing daytime")
    daytimes = [daytimes] if isinstance(daytimes, str) else daytimes
    daytimes = [ ora.Daytime(d) for d in daytimes ]

    return DailySchedule(tz, calendar, daytimes, args)


def jso_to_program(jso):
    if isinstance(jso, str):
        return program.AgentShellProgram(jso)
    elif isinstance(jso, list):
        return program.AgentProgram(jso)
    else:
        # FIXME: Support something reasonable here.
        raise JobSpecificationError("bad program")


def jso_to_reruns(jso):
    return Reruns(
        count       =jso.get("count", 0),
        delay       =jso.get("delay", 0),
        max_delay   =jso.get("max_delay", None),
    )


def jso_to_job(jso, job_id):
    params = jso.get("params", "date")
    params = [params] if isinstance(params, str) else params

    try:
        schedules = jso["schedule"]
    except KeyError:
        schedules = ()
    schedules = (
        [schedules] if isinstance(schedules, dict) 
        else [] if schedules is None
        else schedules
    )
    schedules = [ jso_to_schedule(s) for s in schedules ]

    try:
        program = jso["program"]
    except KeyError:
        raise JobSpecificationError("missing program")
    program = jso_to_program(program)

    reruns = jso_to_reruns(jso.get("reruns", {}))

    return Job(job_id, params, schedules, program, reruns)


def load_yaml(file, job_id):
    jso = yaml.YAML(typ="safe").load(file)
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


#-------------------------------------------------------------------------------

class JobsDir:

    # FIXME: Mapping API?

    def __init__(self, path):
        self.__path = Path(path)
        # FIXME: Detect duplicates.
        self.__jobs = {
            job.job_id: job
            for job in load_yaml_files(path)
        }


    def get_job(self, job_id) -> Job:
        """
        :raise LookupError:
          Can't find `job_id`.
        """
        try:
            return self.__jobs[job_id]
        except KeyError:
            raise LookupError(job_id)


    def get_jobs(self):
        return self.__jobs.values()



