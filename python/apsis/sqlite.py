"""
Persistent state stored in a sqlite file.
"""

import json
import logging
import ora
from   pathlib import Path
import sqlalchemy as sa

from   .runs import Instance, Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# We store times as float seconds from the epoch.

def dump_time(time):
    return time - ora.UNIX_EPOCH


def load_time(time):
    return ora.UNIX_EPOCH + time


METADATA = sa.MetaData()

#-------------------------------------------------------------------------------

TBL_SCHEDULER = sa.Table(
    "scheduler", METADATA,
    sa.Column("stop"        , sa.Float()        , nullable=False),
)


class SchedulerDB:
    """
    Stores the stop time: the frontier to which jobs have been scheduled.
    """

    def __init__(self, engine):
        self.__engine = engine


    def get_stop(self):
        query = sa.select([TBL_SCHEDULER])
        with self.__engine.begin() as conn:
            rows = list(conn.execute(query))
            assert len(rows) <= 1

            if len(rows) == 0:
                # No rows yet; assume current time.
                stop = ora.now()
                conn.execute(
                    TBL_SCHEDULER.insert().values(stop=dump_time(stop)))
            else:
                stop = load_time(rows[0][0])

        return stop

        
    def set_stop(self, stop):
        with self.__engine.begin() as conn:
            conn.execute(TBL_SCHEDULER.update().values(stop=dump_time(stop)))



#-------------------------------------------------------------------------------

# FIXME: For now, we store times and meta as JSON.  To make these searchable,
# we'll need to break them out into tables.

# FIXME: Split out args into a separate table?
# FIXME: Split out instances into a separate table?

# FIXME: Store int enumerals for state?
# FIMXE: Use a TIME column for 'time'?

TBL_RUNS = sa.Table(
    "runs", METADATA,
    sa.Column("run_id"      , sa.String()       , nullable=False),
    sa.Column("timestamp"   , sa.Float()        , nullable=False),
    sa.Column("job_id"      , sa.String()       , nullable=False),
    sa.Column("args"        , sa.String()       , nullable=False),
    sa.Column("state"       , sa.String()       , nullable=False),
    sa.Column("times"       , sa.String()       , nullable=False),
    sa.Column("meta"        , sa.String()       , nullable=False),
    sa.Column("output"      , sa.LargeBinary()  , nullable=True),
)


class RunDB:

    def __init__(self, engine):
        self.__engine = engine


    @staticmethod
    def __values(run):
        times = { n: str(t) for n, t in run.times.items() }
        times = json.dumps(times)
        return dict(
            run_id      =run.run_id,
            timestamp   =dump_time(run.timestamp),
            job_id      =run.inst.job_id,
            args        =json.dumps(run.inst.args),
            state       =run.state.name,
            times       =times,
            meta        =json.dumps(run.meta),
            output      =run.output,
        )


    @staticmethod
    def __query_runs(conn, expr):
        query = sa.select([TBL_RUNS]).where(expr)
        log.info(str(query).replace("\n", " "))

        cursor = conn.execute(query)
        for run_id, timestamp, job_id, args, state, times, meta, output in cursor:
            # FIXME: Inst!
            args            = json.loads(args)
            inst            = Instance(job_id, args)
            run             = Run(inst)
            times           = json.loads(times)
            times           = { n: ora.Time(t) for n, t in times.items() }
            run.run_id      = run_id
            run.timestamp   = load_time(timestamp)
            run.state       = Run.STATE[state]
            run.times       = times
            run.meta        = json.loads(meta)
            run.output      = output
            yield run


    def insert(self, run):
        # FIXME: Check that the run ID doesn't exist already.
        with self.__engine.begin() as conn:
            conn.execute(TBL_RUNS.insert().values(self.__values(run)))


    def update(self, run):
        with self.__engine.begin() as conn:
            conn.execute(
                TBL_RUNS
                .update().where(TBL_RUNS.c.run_id == run.run_id)
                .values(self.__values(run))
            )


    def get(self, run_id):
        with self.__engine.begin() as conn:
            run, = self.__query_runs(conn, TBL_RUNS.c.run_id == run_id)
        return run


    def query(self, *, job_id=None, since=None, until=None):
        where = []
        if job_id is not None:
            where.append(TBL_RUNS.c.job_id == job_id)
        if since is not None:
            where.append(TBL_RUNS.c.rowid >= int(since))
        if until is not None:
            where.append(TBL_RUNS.c.rowid < int(until))

        with self.__engine.begin() as conn:
            # FIMXE: Return only the last record for each run_id?
            runs = list(self.__query_runs(conn, sa.and_(*where)))
        
        return runs



#-------------------------------------------------------------------------------

class SqliteDB:
    """
    A SQLite3 file containing persistent state.
    """

    def __init__(self, path, create=False):
        path    = Path(path).absolute()
        if create and path.exists():
            raise FileExistsError(path)
        if not create and not path.exists():
            raise FileNotFoundError(path)

        url     = self.__get_url(path)
        engine  = sa.create_engine(url)

        if create:
            METADATA.create_all(engine)
        else:
            # FIXME: Check that tables exist.
            pass

        self.run_db         = RunDB(engine)
        self.scheduler_db   = SchedulerDB(engine)


    @classmethod
    def __get_url(Class, path):
        return f"sqlite:///{path}"



