import asyncio
from   contextlib import contextmanager
import itertools
import json
import logging
from   pathlib import Path
import sqlite3

from   .types import Run

log = logging.getLogger(__name__)

# FIXME: For a multithreaded server, need to use multiple connections.

#-------------------------------------------------------------------------------

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



class SQLiteRunDB(RunDB):
    # FIXME: For now, we store times and meta as JSON.  To make these
    # searchable, we'll need to break them out into tables.

    def __init__(self, path, conn):
        super().__init__()
        self.__path = path
        self.__conn = conn


    @classmethod
    def open(Class, path):
        path = Path(path)
        assert path.is_file()
        # FIXME: Check that tables exist.
        return Class(path, sqlite3.connect(str(path)))


    @classmethod
    def create(Class, path):
        path = Path(path)
        assert not path.is_file()
        conn = sqlite3.connect(str(path))
        conn.execute(
            """
            CREATE TABLE runs (
                run_id      TEXT NOT NULL,
                inst_id     TEXT NOT NULL,
                job_id      TEXT NOT NULL,
                number      INTEGER NOT NULL,
                state       TEXT NOT NULL,
                times       TEXT NOT NULL,
                meta        TEXT NOT NULL,
                output      BLOB
            )
            """)
        conn.commit()
        return Class(path, conn)


    def __insert(self, run):
        self.__conn.execute("BEGIN TRANSACTION")
        self.__conn.execute(
            """
            INSERT INTO runs
                (run_id, inst_id, job_id, number, state, times, meta, output)
            VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.inst.inst_id,
                run.inst.job.job_id,
                run.number,
                run.state,
                json.dumps(run.times),
                json.dumps(run.meta),
                run.output,
            )
        )
        (rowid, ), = self.__conn.execute("SELECT MAX(rowid) FROM runs")
        when = str(rowid)
        self.__conn.commit()
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


    def query(self, *, job_id=None, inst_id=None, since=None, until=None):
        query = """
        SELECT
            run_id, inst_id, job_id, number, state, times, meta, output
        FROM runs
        """

        # FIXME: OK maybe we should use SQLite, even the ORM perhaps?
        where = []
        params = []
        if job_id is not None:
            where.append("job_id = ?")
            params.append(job_id)
        if inst_id is not None:
            where.append("inst_id = ?")
            params.append(inst_id)
        if since is not None:
            where.append("row_id >= ?")
            params.append(int(since))
        if until is not None:
            where.appned("row_id < ?")
            params.append(int(until))
        if len(where) > 0:
            query += " WHERE " + " AND ".join(where)

        log.info(query)
        cursor = self.__conn.execute(query, params)
        runs = []
        for run_id, inst_id, job_id, number, state, times, meta, output in cursor:
            # FIXME: Inst!
            run = Run(run_id, inst_id, number)
            run.state = state
            run.times = json.loads(times)
            run.meta = json.loads(meta)
            run.output = output
            runs.append(run)

        (rowid, ), = self.__conn.execute("SELECT MAX(rowid) FROM runs")
        when = str(rowid)

        self.__conn.rollback()
        return when, runs



