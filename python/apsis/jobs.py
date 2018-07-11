from   contextlib import suppress
import ora
import ora.calendar
import os
from   pathlib import Path
import random
import ruamel_yaml as yaml
import string

from   .lib.py import tupleize
from   .program import jso_to_program, program_to_jso
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
        self.job_id     = None if job_id is None else str(job_id)
        self.params     = frozenset( str(p) for p in tupleize(params) )
        self.schedules  = tupleize(schedules)
        self.program    = program
        self.reruns     = reruns



#-------------------------------------------------------------------------------

class JobSpecificationError(Exception):

    pass



# FIXME: This is for daily schedule only!

def jso_to_schedule(jso):
    args = jso.get("args", {})

    try:
        tz = jso["tz"]
    except KeyError:
        raise JobSpecificationError("missing time zone")
    tz = ora.TimeZone(tz)

    calendar = ora.get_calendar(jso.get("calendar", "all"))

    try:
        daytimes = jso["daytime"]
    except KeyError:
        raise JobSpecificationError("missing daytime")
    daytimes = [daytimes] if isinstance(daytimes, str) else daytimes
    daytimes = [ ora.Daytime(d) for d in daytimes ]

    return DailySchedule(tz, calendar, daytimes, args)


def schedule_to_jso(schedule):
    return { 
        "type"  : type(schedule).__qualname__,
        **schedule.to_jso()
    }


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


def job_to_jso(job):
    return {
        "job_id"        : job.job_id,
        "params"        : list(sorted(job.params)),
        "schedules"     : [ schedule_to_jso(s) for s in job.schedules ],
        "program"       : program_to_jso(job.program),
    }


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

# FIXME: Rename get_job() -> get().
# FIXME: Rename get_jobs() -> all().

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



#-------------------------------------------------------------------------------

# FIXME: This feels so awkward.  Is there a better design?

class Jobs:
    """
    Combines a job dir and a job DB.
    """

    def __init__(self, job_dir, job_db):
        self.__job_dir = job_dir
        self.__job_db = job_db


    def get_job(self, job_id) -> Job:
        with suppress(LookupError):
            return self.__job_dir.get_job(job_id)
        return self.__job_db.get(job_id)


    def get_jobs(self):
        yield from self.__job_dir.get_jobs()
        yield from self.__job_db.query()


    def __get_job_id(self):
        # FIXME: Something better.
        return (
            "adhoc-"
            + "".join( random.choice(string.ascii_letters) for _ in range(12) )
        )


    def add(self, job):
        assert job.job_id is None
        job.job_id = self.__get_job_id()

        self.__job_db.insert(job)
                


