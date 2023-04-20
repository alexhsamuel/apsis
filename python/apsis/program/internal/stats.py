import json
import logging

from   apsis.lib.json import check_schema
from   apsis.lib.py import or_none, nstr
from   apsis.runs import template_expand
from   ..base import InternalProgram, ProgramRunning, ProgramSuccess, program_outputs

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

class StatsProgram(InternalProgram):
    """
    A program that collects and dumps Apsis internal stats in JSON format.
    """

    def __init__(self, *, path=None):
        self.__path = path


    def __str__(self):
        res = "internal stats"
        if self.__path is not None:
            res += f"→ {self.__path}"
        return res


    def bind(self, args):
        path = or_none(template_expand)(self.__path, args)
        return type(self)(path=path)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            path = pop("path", nstr, None)
        return cls(path=path)


    def to_jso(self):
        return {
            **super().to_jso(),
            "path": self.__path,
        }


    async def start(self, run_id, apsis):
        run_state = {}
        return ProgramRunning(run_state), self.wait(apsis)


    async def wait(self, apsis):
        stats = json.dumps(apsis.get_stats())
        if self.__path is None:
            outputs = program_outputs(stats.encode())
        else:
            with open(self.__path, "a") as file:
                print(stats, file=file)
            outputs = {}
        return ProgramSuccess(outputs=outputs)


    def reconnect(self, run_id, run_state):
        # FIXME
        assert False


    async def signal(self, run_state, signum):
        pass



