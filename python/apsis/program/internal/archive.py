import asyncio
import logging
import ora

from  ..base import _InternalProgram, ProgramRunning, ProgramSuccess
from  apsis.lib.json import check_schema
from  apsis.runs import template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class ArchiveProgram(_InternalProgram):
    """
    A program that archives old runs from the Apsis database to an archive
    database.

    This program runs within the Apsis process, and blocks all other activities
    while it runs.  Avoid archiving too many runs in a single invocation.

    A run must be retired before it is archived.  If it cannot be retired, it is
    skipped for archiving.
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

        # Make sure all runs are retired; else skip them.
        run_ids = [ r for r in run_ids if apsis.run_store.retire(r) ]

        if len(run_ids) > 0:
            # Archive these runs.
            row_counts = db.archive(self.__path, run_ids)
            # Also vacuum to free space.
            db.vacuum()

        else:
            row_counts = {}

        return ProgramSuccess(meta={
            "run count" : len(run_ids),
            "run_ids"   : run_ids,
            "row counts": row_counts,
        })


    def reconnect(self, run_id, run_state, apsis):
        return asyncio.ensure_future(self.wait(apsis))



