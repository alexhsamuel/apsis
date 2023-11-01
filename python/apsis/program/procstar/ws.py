import logging
import procstar.proto
import procstar.spec
import procstar.ws.server
import uuid

from   apsis.lib.json import check_schema
from   apsis.lib.py import or_none
from   apsis.program import base
from   apsis.runs import join_args, template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# Global procstar service.
server = procstar.ws.server.Server()

ENV = procstar.spec.Proc.Env(
    # Inherit the entire environment from procstar, since it probably
    # includes important configuration.
    inherit=True,
    # Exclude certain Procstar-specific variables.
    vars={
        "PROCSTAR_WS_CERT"  : None,
        "PROCSTAR_WS_KEY"   : None,
        "PROCSTAR_WS_TOKEN" : None,
    }
)


class ProcstarProgram(base.Program):

    def __init__(self, argv, *, group_id=procstar.proto.DEFAULT_GROUP):
        self.__argv = tuple( str(a) for a in argv )
        self.__group_id = group_id


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv        = tuple( template_expand(a, args) for a in self.__argv )
        group_id    = or_none(template_expand)(self.__group_id, args)
        return type(self)(argv, group_id=group_id)


    def to_jso(self):
        return super().to_jso() | {
            "argv"      : list(self.__argv),
            "group_id"  : self.__group_id,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv        = pop("argv")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
        return cls(argv, group_id=group_id)


    async def start(self, run_id, cfg):
        proc_id = str(uuid.uuid4())
        # FIXME
        spec = procstar.spec.make_proc(
            self.__argv,
            fds={
                # FIXME: To file instead?
                "stdout": procstar.spec.Proc.Fd.Capture("memory", "text"),
                # Merge stderr into stdin.
                "stderr": procstar.spec.Proc.Fd.Dup(1),
            },
            env=ENV,
        )
        # FIXME: Handle NoOpenConnectionInGroup and wait.
        try:
            proc = await server.start(proc_id, spec, group_id=self.__group_id)
        except Exception as exc:
            raise base.ProgramError(f"procstar: {exc}")

        # Wait for an initial result.
        res = await anext(proc.results)

        if len(res.errors) > 0:
            # FIXME: Clean up the proc.
            raise base.ProgramError("; ".join(res.errors))

        else:
            # FIXME: Meta.
            run_state = {"proc_id": proc_id}
            done = self.wait(run_id, proc)
            return base.ProgramRunning(run_state), done


    async def wait(self, run_id, proc):
        async for res in proc.results:
            if res.status is None:
                # Not done yet.
                # FIXME: Update anyway.
                pass
            else:
                out = res.fds.stdout.text.encode()
                # FIXME: Compression.
                outputs = base.program_outputs(out)
                if res.status.exit_code == 0:
                    result = base.ProgramSuccess(outputs=outputs)
                else:
                    result = base.ProgramFailure(outputs=outputs)
                # FIXME: Clean up.
                return result


    def reconnect(self, run_id, run_state):
        # FIXME
        raise NotImplementedError("reconnect")


    async def signal(self, run_id, run_state, signal):
        # FIXME
        raise NotImplementedError("signal")



