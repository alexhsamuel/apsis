import asyncio
import logging
import ora
from   pathlib import Path
import sqlalchemy as sa

from  ..base import _InternalProgram, ProgramRunning, ProgramSuccess
from  apsis.lib.json import check_schema
from  apsis.lib.timing import Timer
from  apsis.runs import template_expand
from  apsis.sqlite import SqliteDB, RUN_TABLES, TBL_RUNS, dump_time

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# TODO:
# - check that no archived runs are "live"
# - validate versus `runs.lookback` in cfg
# - int test
# - docs

class ArchiveProgram(_InternalProgram):
    """
    A program that archives old runs from the Apsis database to an archive
    database.

    This program runs within the Apsis process, and blocks all other activities
    while it runs.  Avoid archiving too many runs in a single invocation.
    """

    def __init__(self, *, age, path, count):
        """
        If this archive file doesn't exist, it is created automatically on
        first use; the contianing directory must exist.

        :param age:
          Minimum age in sec for a run to be archived.
        :param path:
          Path to the archive file, a SQLite database in a format similar to the
          Apsis database file.
        :param count:
          Maximum number of runs to archive per run of this program.
        """
        self.__age = age
        self.__path = path
        self.__count = count


    def __str__(self):
        return f"archive age {self.__age} → {self.__path}"


    def bind(self, args):
        age = template_expand(self.__age, args)
        path = template_expand(self.__path, args)
        count = template_expand(self.__count, args)
        return type(self)(age=age, path=path, count=count)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            age = pop("age", float)
            path = pop("path", str)
            count = pop("count", int)
        return cls(age=age, path=path, count=count)


    def to_jso(self):
        return {
            **super().to_jso(),
            "age": self.__age,
            "path": self.__path,
            "count": self.__count,
        }


    async def start(self, run_id, apsis):
        return ProgramRunning({}), self.wait(apsis)


    async def wait(self, apsis):
        archive_path = Path(self.__path)
        try:
            archive_db = SqliteDB.open(archive_path)
        except FileNotFoundError:
            log.info(f"creating: {archive_path}")
            archive_db = SqliteDB.create(archive_path)

        # FIXME: Private attributes.
        src_db = apsis._Apsis__db

        row_counts = {}

        log.debug("starting transaction")
        with (
                Timer() as timer,
                src_db._engine.begin() as src_tx,
                archive_db._engine.begin() as archive_tx
        ):
            # Determine run IDs to archive.
            time = ora.now() - self.__age
            run_ids = [
                r for r, in src_tx.execute(
                    sa.select([TBL_RUNS.c.run_id])
                    .where(TBL_RUNS.c.timestamp < dump_time(time))
                    .order_by(TBL_RUNS.c.timestamp)
                    .limit(self.__count)
                )
            ]
            log.debug(f"archiving runs: {len(run_ids)}")

            # Process all row-related tables.
            for table in (*RUN_TABLES, TBL_RUNS):
                # Clean up any records in the archive that match the run IDs we
                # archive.
                res = archive_tx.execute(
                    sa.delete(table)
                    .where(table.c.run_id.in_(run_ids))
                )
                if res.rowcount > 0:
                    log.warning(
                        f"removed {res.rowcount} rows from {table} "
                        "matching archived runs"
                    )

                # Extract the rows to archive.
                sel = sa.select(table).where(table.c.run_id.in_(run_ids))
                res = src_tx.execute(sel)
                rows = tuple(res.mappings())

                # Write the rows to the archive.
                if len(rows) > 0:
                    res = archive_tx.execute(sa.insert(table), rows)
                    assert res.rowcount == len(rows)

                # Confirm the number of rows.
                (count, ), = archive_tx.execute(
                    sa.select(sa.func.count())
                    .select_from(table)
                    .where(table.c.run_id.in_(run_ids))
                )
                assert count == len(rows), \
                    f"archive {table} contains {count} rows"

                # Remove the rows from the source table.
                res = src_tx.execute(
                    sa.delete(table)
                    .where(table.c.run_id.in_(run_ids))
                )
                assert res.rowcount == len(rows)

                # Keep count of how many rows we archived from each table.
                row_counts[table.name] = len(rows)

        log.info(f"transaction took {timer.elapsed:.3f} s")

        log.info("starting vacuum")
        with Timer() as timer:
            src_db._engine.execute("VACUUM")
        log.info(f"vacuum took {timer.elapsed:.3f} s")

        return ProgramSuccess(meta={
            "run count": len(run_ids),
            "run_ids": run_ids,
            "row counts": row_counts,
        })


    def reconnect(self, run_id, run_state, apsis):
        return asyncio.ensure_future(self.wait(apsis))



