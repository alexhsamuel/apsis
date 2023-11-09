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

# The websockets library is too chatty at DEBUG (but remove this for debugging
# low-level WS or TLS problems).
logging.getLogger("websockets.server").setLevel(logging.INFO)

#-------------------------------------------------------------------------------

# Global procstar service.
server = procstar.ws.server.Server()

ENV = procstar.spec.Proc.Env(
    # Inherit the entire environment from procstar, since it probably
    # includes important configuration.
    inherit=True,
)


def _get_metadata(res):
    """
    Extracts run metadata from a proc result message.
    """
    meta = {
        k: v
        for k in ("errors", )
        if (v := getattr(res, k, None))
    } | {
        k: dict(v.__dict__)
        for k in ("times", "status", "proc_stat", "proc_statm", "rusage", )
        if (v := getattr(res, k, None))
    }

    try:
        meta["procstar_conn"] = dict(res.procstar.conn.__dict__)
        meta["procstar_proc"] = dict(res.procstar.proc.__dict__)
    except AttributeError:
        pass

    return meta


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
        spec = procstar.spec.Proc(
            self.__argv,
            env=ENV,
            fds={
                # FIXME: To file instead?
                "stdout": procstar.spec.Proc.Fd.Capture("memory", "text"),
                # Merge stderr into stdin.
                "stderr": procstar.spec.Proc.Fd.Dup(1),
            },
        )
        # FIXME: Handle NoOpenConnectionInGroup and wait.
        try:
            proc = await server.start(proc_id, spec, group_id=self.__group_id)
        except Exception as exc:
            raise base.ProgramError(f"procstar: {exc}")

        # Wait for an initial result.
        res = await anext(proc.results)

        if len(res.errors) > 0:
            # Clean up the process.
            try:
                await server.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")

            raise base.ProgramError(
                "; ".join(res.errors), meta=_get_metadata(res))

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
                meta = _get_metadata(res)
                # FIXME: Compression.
                outputs = base.program_outputs(out)

                # Clean up the process.
                try:
                    await server.delete(proc.proc_id)
                except Exception as exc:
                    log.error(f"delete {proc.proc_id}: {exc}")

                if len(res.errors) > 0:
                    message = "; ".join(res.errors)
                    raise base.ProgramError(
                        message,
                        outputs =outputs,
                        meta    =meta,
                    )

                elif res.status.exit_code == 0:
                    return base.ProgramSuccess(
                        outputs =outputs,
                        meta    =meta,
                    )

                else:
                    message = "program failed: "
                    if res.status.signum is None:
                        message += f"exit code {res.status.exit_code}"
                    else:
                        # FIXME: Include signal name, which should be in result.
                        message += f"kill by signal {res.status.signum}"
                    raise base.ProgramFailure(
                        message,
                        outputs =outputs,
                        meta    =meta,
                    )


    def reconnect(self, run_id, run_state):
        # FIXME
        raise NotImplementedError("reconnect")


    async def signal(self, run_id, run_state, signal):
        # FIXME
        raise NotImplementedError("signal")



