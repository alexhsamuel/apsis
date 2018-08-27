"""
Persistent state stored in a sqlite file.
"""

import logging
import ora
from   pathlib import Path
import sqlalchemy as sa
import ujson

from   .jobs import jso_to_job, job_to_jso
from   .runs import Instance, Run
from   .program import program_to_jso, program_from_jso, Output, OutputMetadata

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# We store times as float seconds from the epoch.

def dump_time(time):
    return time - ora.UNIX_EPOCH


def load_time(time):
    return ora.UNIX_EPOCH + time


METADATA = sa.MetaData()

#-------------------------------------------------------------------------------

TBL_CLOCK = sa.Table(
    "clock", METADATA, 
    sa.Column("time", sa.Float(), nullable=False),
)


class ClockDB:
    """
    Stores the most recent application time.
    """

    # We use a DB-API connection and SQL statements because it's faster than
    # the SQLAlchemy ORM.

    def __init__(self, engine):
        self.__connection = engine.connect().connection

        (length, ), = self.__connection.execute("SELECT COUNT(*) FROM clock")
        if length == 0:
            time = ora.now() - ora.UNIX_EPOCH
            self.__connection.execute("INSERT INTO clock VALUES (?)", (time, ))
            self.__connection.commit()
        else:
            assert length == 1


    def get_time(self):
        (time, ), = self.__connection.execute("SELECT time FROM clock")
        return time + ora.UNIX_EPOCH


    def set_time(self, time):
        time -= ora.UNIX_EPOCH
        self.__connection.execute("UPDATE clock SET time = ?", (time, ))
        self.__connection.commit()



#-------------------------------------------------------------------------------

TBL_JOBS = sa.Table(
  "jobs", METADATA,
  sa.Column("job_id"        , sa.String()       , nullable=False),
  sa.Column("job"           , sa.String()       , nullable=False),
)

class JobDB:

    def __init__(self, engine):
        self.__engine = engine


    def insert(self, job):
        # FIXME: Check that the job ID doesn't exist already
        with self.__engine.begin() as conn:
            conn.execute(TBL_JOBS.insert().values(
                job_id  =job.job_id,
                job     =ujson.dumps(job_to_jso(job)),
            ))


    def get(self, job_id):
        with self.__engine.begin() as conn:
            query = sa.select([TBL_JOBS]).where(TBL_JOBS.c.job_id == job_id)
            rows = list(conn.execute(query))
            assert len(rows) <= 1

            if len(rows) == 0:
                raise LookupError(job_id)
            else:
                (_, job), = rows
                return jso_to_job(ujson.loads(job), job_id)


    def query(self):
        query = sa.select([TBL_JOBS])
        with self.__engine.begin() as conn:
            for job_id, job in conn.execute(query):
                yield jso_to_job(ujson.loads(job), job_id)



#-------------------------------------------------------------------------------

# FIXME: For now, we store times and meta as JSON.  To make these searchable,
# we'll need to break them out into tables.

# FIXME: Split out args into a separate table?
# FIXME: Split out instances into a separate table?

# FIXME: Store int enumerals for state?
# FIMXE: Use a TIME column for 'time'?

TBL_RUNS = sa.Table(
    "runs", METADATA,
    sa.Column("rowid"       , sa.Integer()      , primary_key=True),
    sa.Column("run_id"      , sa.String()       , nullable=False),
    sa.Column("timestamp"   , sa.Float()        , nullable=False),
    sa.Column("job_id"      , sa.String()       , nullable=False),
    sa.Column("args"        , sa.String()       , nullable=False),
    sa.Column("state"       , sa.String()       , nullable=False),
    sa.Column("program"     , sa.String()       , nullable=True),
    sa.Column("times"       , sa.String()       , nullable=False),
    sa.Column("meta"        , sa.String()       , nullable=False),
    sa.Column("message"     , sa.String()       , nullable=True),
    sa.Column("run_state"   , sa.String()       , nullable=True),
    sa.Column("rerun"       , sa.String()       , nullable=True),
    sa.Column("expected"    , sa.Boolean()      , nullable=False),
)


class RunDB:

    # For runs in the database (either inserted into or loaded from), we stash
    # the sqlite rowid in the Run._rowid attribute.

    def __init__(self, engine):
        self.__engine = engine


    @staticmethod
    def __values(run):
        assert run.run_id.startswith("r")
        rowid = int(run.run_id[1 :])

        program = (
            None if run.program is None
            else ujson.dumps(program_to_jso(run.program))
        )

        times = { n: str(t) for n, t in run.times.items() }
        times = ujson.dumps(times)
        
        return dict(
            rowid       =rowid,
            run_id      =run.run_id,
            timestamp   =dump_time(run.timestamp),
            job_id      =run.inst.job_id,
            args        =ujson.dumps(run.inst.args),
            state       =run.state.name,
            program     =program,
            times       =times,
            meta        =ujson.dumps(run.meta),
            message     =run.message,
            run_state   =ujson.dumps(run.run_state),
            rerun       =run.rerun,
            expected    =run.expected,
        )


    @staticmethod
    def __query_runs(conn, expr):
        query = sa.select([TBL_RUNS]).where(expr)
        log.debug(str(query).replace("\n", " "))

        cursor = conn.execute(query)
        for (
                rowid, run_id, timestamp, job_id, args, state, program, times,
                meta, message, run_state, rerun, expected,
        ) in cursor:
            if program is not None:
                program     = program_from_jso(ujson.loads(program))

            times           = ujson.loads(times)
            times           = { n: ora.Time(t) for n, t in times.items() }

            args            = ujson.loads(args)
            inst            = Instance(job_id, args)
            run             = Run(inst, rerun=rerun, expected=expected)

            run.run_id      = run_id
            run.timestamp   = load_time(timestamp)
            run.state       = Run.STATE[state]
            run.program     = program
            run.times       = times
            run.meta        = ujson.loads(meta)
            run.message     = message
            run.run_state   = ujson.loads(run_state)
            run._rowid      = rowid
            yield run


    def upsert(self, run):
        try:
            # Get the rowid; if it's missing, this run isn't in the table.
            rowid = run._rowid

        except AttributeError:
            # This run isn't in the database yet.
            values = self.__values(run)
            statement = TBL_RUNS.insert().values(values)
            log.debug(statement)
            with self.__engine.begin() as conn:
                conn.execute(statement)
            run._rowid = values["rowid"]

        else:
            # Update the existing row.
            statement = TBL_RUNS.update().where(
                TBL_RUNS.c.rowid == rowid).values(self.__values(run))
            log.debug(statement)
            with self.__engine.begin() as conn:
                conn.execute(statement)


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

class OutputDB:
    """
    We store even large outputs in the SQLite database, which should generally
    be efficient.  See https://www.sqlite.org/intern-v-extern-blob.html.
    """

    TBL_OUTPUT = sa.Table(
        "output", METADATA,
        sa.Column("run_id"      , sa.String()   , nullable=False),
        sa.Column("output_id"   , sa.String()   , nullable=False),
        sa.Column("name"        , sa.String()   , nullable=False),
        sa.Column("content_type", sa.String()   , nullable=False),
        sa.Column("length"      , sa.Integer()  , nullable=False),
        sa.Column("compression" , sa.String()   , nullable=True),
        sa.Column("data"        , sa.Binary()   , nullable=False),
        sa.PrimaryKeyConstraint("run_id", "output_id")
    )

    def __init__(self, engine):
        self.__engine = engine

        
    def add(self, run_id: str, output_id: str, output: Output):
        values = {
            "run_id"        : run_id,
            "output_id"     : output_id,
            "name"          : output.metadata.name,
            "content_type"  : output.metadata.content_type,
            "length"        : output.metadata.length,
            "compression"   : output.compression,
            "data"          : output.data,
        }
        with self.__engine.begin() as conn:
            conn.execute(self.TBL_OUTPUT.insert().values(**values))


    def get_metadata(self, run_id) -> OutputMetadata:
        """
        Returns all output metadata for run `run_id`.

        :return:
          A mapping from output ID to `OutputMetadata` instances.  If no output
          is stored for `run_id`, returns an empty dict.
        """
        cols    = self.TBL_OUTPUT.c
        columns = [cols.output_id, cols.name, cols.content_type, cols.length]
        query   = sa.select(columns).where(cols.run_id == run_id)
        return {
            r[0]: OutputMetadata(name=r[1], length=r[3], content_type=r[2])
            for r in self.__engine.execute(query)
        }


    def get_data(self, run_id, output_id) -> bytes:
        cols = self.TBL_OUTPUT.c
        query = (
            sa.select([cols.compression, cols.data])
            .where((cols.run_id == run_id) & ((cols.output_id == output_id)))
        )
        rows = list(self.__engine.execute(query))
        if len(rows) == 0:
            raise LookupError(f"no output {output_id} for {run_id}")
        else:
            (compression, data), = rows
            if compression is None:
                return data
            else:
                raise NotImplementedError(f"compression: f{compression}")



#-------------------------------------------------------------------------------

class SqliteDB:
    """
    A SQLite3 file containing persistent state.
    """

    def __init__(self, engine):
        """
        :param path:
          Path to SQLite file.  If `None`, use a memory DB (for testing).
        """
        self.clock_db   = ClockDB(engine)
        self.job_db     = JobDB(engine)
        self.run_db     = RunDB(engine)
        self.output_db  = OutputDB(engine)


    @classmethod
    def __get_engine(Class, path):
        url = "sqlite://" if path is None else f"sqlite:///{path}"
        return sa.create_engine(url)


    @classmethod
    def create(Class, path):
        """
        Creates a new database.

        :param path:
          The database path, which must not already exist.
        :return:
          The new database.
        """
        if path is not None:
            path = Path(path).absolute()
            if path.exists():
                raise FileExistsError(path)
        
        engine  = Class.__get_engine(path)
        METADATA.create_all(engine)
        return Class(engine)


    @classmethod
    def open(Class, path):
        if path is not None:
            path = Path(path).absolute()
            if not path.exists():
                raise FileNotFoundError(path)

        engine  = Class.__get_engine(path)
        # FIXME: Check that tables exist.
        return Class(engine)



