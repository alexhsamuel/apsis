from   aslib.py import format_ctor
import json
from   pathlib import Path
from   typing import *

from   . import schedule

#-------------------------------------------------------------------------------

class Job:

    def __init__(self, id, schedule, program):
        self.__id       = str(id)
        self.__schedule = schedule
        self.__program  = program


    @property
    def id(self):
        return self.__id


    @property
    def schedule(self):
        return self.__schedule


    @property
    def program(self):
        return self.__program


    def to_jso(self):
        from . import program
        return {
            "$id"       : self.__id,
            "schedule"  : schedule.to_jso(self.__schedule),
            "program"   : program.to_jso(self.__program),
        }


    @classmethod
    def from_jso(class_, jso):
        return class_(
            jso["$id"],
            schedule.from_jso(jso["schedule"]),
            program.from_jso(jso["program"]),
        )



class Instance:

    def __init__(self, id, job, time):
        self.__id       = id
        self.__job      = job
        self.__time     = time


    def __repr__(self):
        return format_ctor(self, self.__id, self.__job, self.__time)


    @property
    def id(self):
        return self.__id


    @property
    def job(self):
        return self.__job


    @property
    def time(self):
        return self.__time


    def to_jso(self):
        return {
            "$id"       : self.__id,
            "job"       : self.__job.to_jso(),
            "time"      : str(self.__time),
        }



class Run:

    def __init__(self, id, inst):
        self.__id   = id
        self.__inst = inst


    @property
    def id(self):
        return self.__id


    @property
    def inst(self):
        return self.__inst


    def to_jso(self):
        return {
            "$id"       : self.__id,
            "inst"      : self.__inst.to_jso(),
        }



#-------------------------------------------------------------------------------

def load_job_file_json(path: Path) -> Job:
    with open(path) as file:
        jso = json.load(file)
    jso.setdefault("$id", path.with_suffix("").name)
    return Job.from_jso(jso)


def load_job_dir(path: Path) -> Iterable[Job]:
    """
    Loads job files in `path`.

    Skips files that do not have a supported extension.
    """
    path = Path(path)
    for entry in path.iterdir():
        if entry.suffix == ".json":
            yield load_job_file_json(entry)
        else:
            # Skip it.
            pass


