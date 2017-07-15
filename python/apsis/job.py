from   aslib.py import format_ctor, tupleize
from   cron import *
import json
from   pathlib import Path
from   typing import *

#-------------------------------------------------------------------------------

def format_time(time):
    # FIXME: For now, assume 1 s resolution.
    return format(time, "%Y-%m-%d %H:%M:%S")


class Job:

    def __init__(self, job_id, params, schedule, program):
        self.job_id     = str(job_id)
        self.params     = frozenset( str(p) for p in tupleize(params) )
        self.schedule   = schedule
        self.program    = program


    def to_jso(self):
        from . import program, schedule
        return {
            "job_id"    : self.job_id,
            "params"    : list(sorted(self.params)),
            "schedule"  : schedule.to_jso(self.schedule),
            "program"   : program.to_jso(self.program),
        }


    @classmethod
    def from_jso(class_, jso):
        from . import program, schedule
        return class_(
            jso["job_id"],
            jso["params"],
            schedule.from_jso(jso["schedule"]),
            program.from_jso(jso["program"]),
        )



class Instance:

    def __init__(self, inst_id, job, args, time):
        args = { str(k): str(v) for k, v in args.items() }
        assert args.keys() == job.params

        self.inst_id    = str(inst_id)
        self.job        = job
        self.args       = args
        self.time       = Time(time)


    def __repr__(self):
        return format_ctor(self, self.inst_id, self.job, self.args, self.time)


    def __lt__(self, other):
        return (
            self.inst_id < other.inst_id if isinstance(other, Instance)
            else NotSupported
        )


    def to_jso(self):
        return {
            "inst_id"   : self.inst_id,
            "job"       : self.job.to_jso(),
            "args"      : self.args,
            "time"      : format_time(self.time),
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


