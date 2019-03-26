"""
Persistent state stored in a sqlite file.
"""

import logging
import ora
from   pathlib import Path
import sqlalchemy as sa
import ujson

from   .jobs import jso_to_job, job_to_jso, JobSpecificationError
from   .runs import Instance, Run
from   .program import program_to_jso, program_from_jso, Output, OutputMetadata

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# We store times as float seconds from the epoch.

def dump_time(time):
    return time - ora.UNIX_EPOCH


def load_time(time):
    return ora.UNIX_EPOCH + time


def _get_max_run_id_num(engine, table):
    with engine.begin() as conn:
        rows = list(conn.execute(
            f"SELECT MAX(CAST(SUBSTR(run_id, 2) AS DECIMAL)) FROM {table}"))
    (max_num, ), = rows
    return 0 if max_num is None else max_num


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


    def query(self, *, ad_hoc=None):
        query = sa.select([TBL_JOBS])
        with self.__engine.begin() as conn:
            for job_id, job in conn.execute(query):
                # FIXME: Filter ad hoc jobs in the query.
                try:
                    job = jso_to_job(ujson.loads(job), job_id)
                except JobSpecificationError as exc:
                    logging.error(f"failed to load job from DB: {exc}")
                    continue
                if ad_hoc is None or job.ad_hoc == ad_hoc:
                    yield job



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
)


class RunDB:

    # For runs in the database (either inserted into or loaded from), we stash
    # the sqlite rowid in the Run._rowid attribute.

    def __init__(self, engine):
        self.__engine = engine
        self.__connection = engine.raw_connection()
        # FIXME: Do we need to clean this up?


    @staticmethod
    def __query_runs(conn, expr):
        query = sa.select([TBL_RUNS]).where(expr)
        log.debug(str(query).replace("\n", " "))

        cursor = conn.execute(query)
        for (
                rowid, run_id, timestamp, job_id, args, state, program, times,
                meta, message, run_state, rerun,
        ) in cursor:
            if program is not None:
                program     = program_from_jso(ujson.loads(program))

            times           = ujson.loads(times)
            times           = { n: ora.Time(t) for n, t in times.items() }

            args            = ujson.loads(args)
            inst            = Instance(job_id, args)
            run             = Run(inst, rerun=rerun)

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
        assert run.run_id.startswith("r")
        assert not run.expected
        rowid = int(run.run_id[1 :])

        program = (
            None if run.program is None
            else ujson.dumps(program_to_jso(run.program))
        )
        # FIXME: Precos, same as program.

        times = { n: str(t) for n, t in run.times.items() }
        
        # We use SQL instead of SQLAlchemy for performance.
        values = (
            run.run_id,
            dump_time(run.timestamp),
            run.inst.job_id,
            ujson.dumps(run.inst.args),
            run.state.name,
            program,
            ujson.dumps(times),
            ujson.dumps(run.meta),
            run.message,
            ujson.dumps(run.run_state),
            run.rerun,
            rowid,
        )

        try:
            # Get the rowid; if it's missing, this run isn't in the table.
            run._rowid

        except AttributeError:
            # This run isn't in the database yet.
            self.__connection.connection.execute("""
                INSERT INTO runs (
                    run_id, 
                    timestamp, 
                    job_id, 
                    args, 
                    state, 
                    program, 
                    times, 
                    meta, 
                    message, 
                    run_state, 
                    rerun, 
                    rowid
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, values)
            self.__connection.connection.commit()
            run._rowid = values[-1]

        else:
            # Update the existing row.
            self.__connection.connection.execute("""
                UPDATE runs SET
                    run_id      = ?, 
                    timestamp   = ?, 
                    job_id      = ?, 
                    args        = ?, 
                    state       = ?, 
                    program     = ?, 
                    times       = ?, 
                    meta        = ?, 
                    message     = ?, 
                    run_state   = ?, 
                    rerun       = ?
                WHERE rowid = ?
            """, values)
            self.__connection.connection.commit()


    def get(self, run_id):
        with self.__engine.begin() as conn:
            run, = self.__query_runs(conn, TBL_RUNS.c.run_id == run_id)
        return run


    def query(self, *, job_id=None, since=None, until=None):
        log.debug(f"query job_id={job_id} since={since} until={until}")
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
        
        log.debug(f"query returned {len(runs)} runs")
        return runs


    def get_max_run_id_num(self):
        return _get_max_run_id_num(self.__engine, "runs")



#-------------------------------------------------------------------------------

class RunHistoryDB:

    TABLE = sa.Table(
        "run_history", METADATA,
        sa.Column("run_id"      , sa.String()   , nullable=False),
        sa.Column("timestamp"   , sa.Float      , nullable=False),
        sa.Column("message"     , sa.String()   , nullable=False),
        sa.Index("idx_run_id", "run_id"),
    )

    def __init__(self, engine):
        self.__engine = engine
        self.__cache = {}


    def cache(self, run_id: str, timestamp: ora.Time, message: str):
        values = {
            "run_id"    : run_id,
            "timestamp" : timestamp,
            "message"   : str(message),
        }
        self.__cache.setdefault(run_id, []).append(values)


    def insert(self, run_id: str, timestamp: ora.Time, message: str):
        values = {
            "run_id"    : run_id,
            "timestamp" : dump_time(timestamp),
            "message"   : str(message),
        }
        with self.__engine.begin() as conn:
            conn.execute(self.TABLE.insert().values(**values))


    def flush(self, run_id):
        """
        FLushes cached run history to the database.
        """
        cache = self.__cache.pop(run_id, ())
        if len(cache) > 0:
            for item in cache:
                item["timestamp"] = dump_time(item["timestamp"])
            with self.__engine.begin() as conn:
                conn.execute(self.TABLE.insert().values(cache))


    def query(self, *, run_id: str):
        log.debug(f"query run history run_id={run_id}")
        where = self.TABLE.c.run_id == run_id

        # Respond with cached values.
        yield from self.__cache.get(run_id, ())

        # Now query the database.
        with self.__engine.begin() as conn:
            rows = list(conn.execute(sa.select([self.TABLE]).where(where)))

        for run_id, timestamp, _, message in rows:
            yield {
                "run_id"    : run_id,
                "timestamp" : load_time(timestamp),
                "message"   : message,
            }


    def get_max_run_id_num(self):
        return _get_max_run_id_num(self.__engine, "run_history")



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
                raise NotImplementedError(f"compression: {compression}")



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
        self.clock_db       = ClockDB(engine)
        self.job_db         = JobDB(engine)
        self.run_db         = RunDB(engine)
        self.run_history_db = RunHistoryDB(engine)
        self.output_db      = OutputDB(engine)


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
    def migrate(Class, path):
        """
        (Attempts to) migrate the database at `path`.
        """
        assert path is not None
        path = Path(path).absolute()
        if not path.exists():
            raise FileNotFoundError(path)

        engine = Class.__get_engine(path)
        METADATA.create_all(engine)

        # Clean up expected runs; these used to be persisted.
        try:
            engine.execute("DELETE FROM runs WHERE expected")
        except sa.exc.OperationalError:
            # Column may not exist.
            pass


    @classmethod
    def open(Class, path):
        if path is not None:
            path = Path(path).absolute()
            if not path.exists():
                raise FileNotFoundError(path)

        engine  = Class.__get_engine(path)
        # FIXME: Check that tables exist.
        return Class(engine)


    def get_max_run_id_num(self):
        """
        :return:
          The largest run ID number in use, or 0.
        """
        return max(
            self.run_db.get_max_run_id_num(),
            self.run_history_db.get_max_run_id_num(),
        )



