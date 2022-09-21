import logging
from   pathlib import Path

from   apsis.lib import json, py
from   apsis.runs import get_bind_args, template_expand
from   .base import Condition

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class FileExists(Condition):

    def __init__(self, path):
        self.path = Path(path)


    def __repr__(self):
        return py.format_ctor(self, self.path)


    def __str__(self):
        return f"file {self.path} exists"


    def to_jso(self):
        return {
            **super().to_jso(),
            "path": str(self.path),
        }


    @classmethod
    def from_jso(cls, jso):
        with json.check_schema(jso) as pop:
            return cls(pop("path", str))


    def bind(self, run, jobs):
        bind_args = get_bind_args(run)
        path = template_expand(self.path, bind_args)
        return type(self)(path)


    poll_interval = 10

    async def check(self):
        log.info(f"checking for {self.path}")
        return self.path.is_file()



