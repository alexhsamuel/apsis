import asyncio
from   contextlib import contextmanager
import itertools
import json
import logging
from   pathlib import Path
import sqlalchemy as sa

from   .lib.itr import take_last
from   .types import Run

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.
class RunDB:

    def __init__(self):
        self.__queues = set()
        self.run_ids = ( "run" + str(i) for i in itertools.count() )


    @contextmanager
    def query_live(self, *, since=None, **kw_args):
        queue = asyncio.Queue()
        self.__queues.add(queue)

        when, runs = self.query(since=since, **kw_args)
        queue.put_nowait((when, runs))

        try:
            yield queue
        finally:
            self.__queues.remove(queue)


    def _send(self, when, run):
        for queue in self.__queues:
            queue.put_nowait((when, [run]))



METADATA = sa.MetaData()

# FIXME: For now, we store times and meta as JSON.  To make these searchable,
# we'll need to break them out into tables.

TBL_RUNS = sa.Table(
    "runs", METADATA,
    sa.Column("run_id"      , sa.String()       , nullable=False),
    sa.Column("inst_id"     , sa.String()       , nullable=False),
    sa.Column("job_id"      , sa.String()       , nullable=False),
    sa.Column("number"      , sa.Integer()      , nullable=False),
    sa.Column("state"       , sa.String()       , nullable=False),
    sa.Column("times"       , sa.String()       , nullable=False),
    sa.Column("meta"        , sa.String()       , nullable=False),
    sa.Column("output"      , sa.LargeBinary()  , nullable=True),
)

SQL_MAX_ROWID = sa.text("SELECT MAX(rowid) FROM runs")


class SQLAlchemyRunDB(RunDB):
    # FIXME: Currently depends on SQLite-specific rowid.

    def __init__(self, engine):
        super().__init__()
        self.__engine = engine


    @classmethod
    def __get_url(Class, path):
        # For now, sqlite only.
        return f"sqlite:///{path}"


    @classmethod
    def open(Class, path):
        path = Path(path).absolute()
        assert path.is_file()
        url = Class.__get_url(path)
        engine = sa.create_engine(url)
        # FIXME: Check that tables exist.
        return Class(engine)


    @classmethod
    def create(Class, path):
        path = Path(path).absolute()
        assert not path.is_file()
        url = Class.__get_url(path)
        engine = sa.create_engine(url)
        METADATA.create_all(engine)
        return Class(engine)


    def __insert(self, run):
        with self.__engine.begin() as conn:
            conn.execute(TBL_RUNS.insert().values(
                run_id  =run.run_id,
                inst_id =run.inst.inst_id,
                job_id  =run.job_id,
                number  =run.number,
                state   =run.state,
                times   =json.dumps(run.times),
                meta    =json.dumps(run.meta),
                output  =run.output,
            ))
            rowid = conn.execute(SQL_MAX_ROWID).scalar()

        when = str(rowid)
        return when


    async def add(self, run):
        # FIXME: Check that the run ID doesn't exist already.
        when = self.__insert(run)
        self._send(when, run)


    # FIXME: Sloppy API.  Are we mutating the run, or replacing it?
    async def update(self, run):
        # FIXME: Check that the run ID exists already.
        when = self.__insert(run)
        self._send(when, run)


    def __now(self, conn):
        rowid = conn.execute(sa.text("SELECT MAX(rowid) FROM runs")).scalar()
        return str(rowid)


    def __get_runs(self, conn, expr):
        query = sa.select([TBL_RUNS]).where(expr)
        log.info(query)

        cursor = conn.execute(query)
        for (
                run_id, inst_id, job_id, number, state, times, meta, output 
        ) in cursor:
            # FIXME: Inst!
            run = Run(run_id, inst_id, number)
            run.state = state
            run.times = json.loads(times)
            run.meta = json.loads(meta)
            run.output = output
            yield run


    async def get(self, run_id):
        with self.__engine.begin() as conn:
            runs = self.__get_runs(conn, TBL_RUNS.c.run_id == run_id)
            # FIXME: Do this in the database instead.
            run = take_last(runs)
            when = self.__now(conn)
        return when, run


    def query(self, *, job_id=None, inst_id=None, since=None, until=None):
        where = []
        if job_id is not None:
            where.append(TBL_RUNS.c.job_id == job_id)
        if inst_id is not None:
            where.append(TBL_RUNS.c.inst_id == inst_id)
        if since is not None:
            where.append(TBL_RUNS.c.rowid >= int(since))
        if until is not None:
            where.append(TBL_RUNS.c.rowid < int(until))

        with self.__engine.begin() as conn:
            # FIMXE: Return only the last record for each run_id?
            runs = list(self.__get_runs(conn, sa.and_(*where)))
            when = self.__now(conn)
        
        return when, runs



