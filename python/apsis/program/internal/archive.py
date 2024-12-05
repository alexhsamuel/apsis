import asyncio
import logging
import ora

from   ..base import _InternalProgram, ProgramRunning, ProgramSuccess
from   apsis.lib.json import check_schema
from   apsis.lib.parse import parse_duration
from   apsis.runs import template_expand

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

    def __init__(self, *, age, path, count, chunk_size=None):
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
        :param chunk_size:
          Number of runs to archive in one chunk.  Each chunk is blocking.
        """
        self.__age          = age
        self.__path         = path
        self.__count        = count
        self.__chunk_size   = chunk_size


    def __str__(self):
        return f"archive age {self.__age} → {self.__path}"


    def bind(self, args):
        return type(self)(
            age         = parse_duration(template_expand(self.__age, args)),
            path        = template_expand(self.__path, args),
            count       = int(template_expand(self.__count, args)),
            chunk_size  = None if self.__chunk_size is None
                          else int(template_expand(self.__chunk_size, args)),
        )


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            age         = pop("age")
            path        = pop("path", str)
            count       = pop("count", int)
            chunk_size  = pop("chunk_size", int, None)
        return cls(age=age, path=path, count=count, chunk_size=chunk_size)


    def to_jso(self):
        return {
            **super().to_jso(),
            "age"   : self.__age,
            "path"  : self.__path,
            "count" : self.__count,
            **(
                {} if self.__chunk_size is None
                else {"chunk_size": self.__chunk_size}
            ),
        }


    async def start(self, run_id, apsis):
        return ProgramRunning({}), self.wait(apsis)


    async def wait(self, apsis):
        # FIXME: Private attributes.
        db = apsis._Apsis__db

        if not (self.__chunk_size is None or 0 < self.__chunk_size):
            raise ValueError("nonpositive chunk size")

        row_counts = {}
        meta = {
            "run count" : 0,
            "run_ids"   : [],
            "row counts": row_counts
        }

        count = self.__count
        while count > 0:
            chunk = (
                count if self.__chunk_size is None
                else min(count, self.__chunk_size)
            )
            run_ids = db.get_archive_run_ids(
                before  =ora.now() - self.__age,
                count   =chunk,
            )
            count -= chunk

            # Make sure all runs are retired; else skip them.
            run_ids = [ r for r in run_ids if apsis.run_store.retire(r) ]

            if len(run_ids) > 0:
                # Archive these runs.
                chunk_row_counts = db.archive(self.__path, run_ids)
                # Accumulate metadata.
                meta["run count"] += len(run_ids)
                meta["run_ids"].extend(run_ids)
                for key, value in chunk_row_counts.items():
                    row_counts[key] = row_counts.get(key, 0) + value
                # Also vacuum to free space.
                db.vacuum()

        return ProgramSuccess(meta=meta)


    def reconnect(self, run_id, run_state, apsis):
        return asyncio.ensure_future(self.wait(apsis))



