import asyncio
from   contextlib import closing
import logging
import ora
from   pathlib import Path

from  ..base import _InternalProgram, ProgramRunning, ProgramSuccess
from  apsis.lib.json import check_schema
from  apsis.runs import template_expand
from  apsis.sqlite import SqliteDB

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# TODO:
# - validate versus `runs.lookback` in cfg
# - int test
# - docs
# - clean up old `apsisctl archive`

class ArchiveProgram(_InternalProgram):
    """
    A program that archives old runs from the Apsis database to an archive
    database.

    This program runs within the Apsis process, and blocks all other activities
    while it runs.  Avoid archiving too many runs in a single invocation.

    Only runs that have already been retired may be archived.  Make sure the
    `runs.lookback` configuration is set to a smaller value than the `age`
    argument used when archiving.
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
        age = float(template_expand(self.__age, args))
        path = template_expand(self.__path, args)
        count = int(template_expand(self.__count, args))
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
        # FIXME: Private attributes.
        db = apsis._Apsis__db

        run_ids = db.get_archive_run_ids(
            before  =ora.now() - self.__age,
            count   =self.__count,
        )

        # If any runs to archive are still in the run store, exclude them.
        live_run_ids = { r for r in run_ids if r in apsis.run_store }
        if len(live_run_ids) > 0:
            log.warning(f"{len(live_run_ids)} of {len(run_ids)} for archive are live")
            run_ids = [ r for r in run_ids if r not in live_run_ids ]

        if len(run_ids) > 0:
            archive_path = Path(self.__path)
            try:
                archive_db = SqliteDB.open(archive_path)
            except FileNotFoundError:
                log.info(f"creating: {archive_path}")
                archive_db = SqliteDB.create(archive_path)
            # Archive these runs.
            with closing(archive_db):
                row_counts = db.archive(archive_db, run_ids)
            # Also vacuum to free space.
            db.vacuum()

        else:
            row_counts = {}

        return ProgramSuccess(meta={
            "run count" : len(run_ids),
            "run_ids"   : run_ids,
            "row counts": row_counts,
            "live_runs" : len(live_run_ids),
        })


    def reconnect(self, run_id, run_state, apsis):
        return asyncio.ensure_future(self.wait(apsis))



