import logging
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

def _get_metadata(result):
    """
    Extracts run metadata from a proc result message.
    """
    meta = {
        k: v
        for k in ("errors", )
        if (v := getattr(result, k, None))
    } | {
        k: dict(v.__dict__)
        for k in ("times", "status", "proc_stat", "proc_statm", "rusage", )
        if (v := getattr(result, k, None))
    }

    try:
        meta["procstar_conn"] = dict(result.procstar.conn.__dict__)
        meta["procstar_proc"] = dict(result.procstar.proc.__dict__)
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


    def make_spec(self):
        """
        Constructs the procstar proc spec for this program.
        """
        return procstar.spec.Proc(
            self.__argv,
            env=procstar.spec.Proc.Env(
                # Inherit the entire environment from procstar, since it probably
                # includes important configuration.
                inherit=True,
            ),
            fds={
                # FIXME: To file instead?
                "stdout": procstar.spec.Proc.Fd.Capture("memory", "text"),
                # Merge stderr into stdin.
                "stderr": procstar.spec.Proc.Fd.Dup(1),
            },
        )


    async def start(self, run_id, cfg):
        proc_id = str(uuid.uuid4())
        spec = self.make_spec()
        # FIXME: Handle NoOpenConnectionInGroup and wait.
        try:
            proc = await server.start(proc_id, spec, group_id=self.__group_id)
        except Exception as exc:
            raise base.ProgramError(f"procstar: {exc}")

        # Wait for an initial result.
        try:
            try:
                result = await anext(proc.results)
            except Exception as exc:
                raise base.ProgramError(str(exc))
            else:
                if len(result.errors) > 0:
                    raise base.ProgramError(
                        "; ".join(data.errors),
                        meta=_get_metadata(result)
                    )

                # FIXME: Metadata.
                run_state = {"proc_id": proc_id}
                done = self.wait(run_id, proc)
                return base.ProgramRunning(run_state), done

        except base.ProgramError:
            # Clean up the process.
            try:
                await server.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")
            raise


    def __on_complete(self, proc, result):
        out = result.fds.stdout.text.encode()
        meta = _get_metadata(result)
        # FIXME: Compression.
        outputs = base.program_outputs(out)

        if len(result.errors) > 0:
            message = "; ".join(result.errors)
            raise base.ProgramError(
                message,
                outputs =outputs,
                meta    =meta,
            )

        elif result.status.exit_code == 0:
            return base.ProgramSuccess(
                outputs =outputs,
                meta    =meta,
            )

        else:
            message = "program failed: "
            if result.status.signum is None:
                message += f"exit code {result.status.exit_code}"
            else:
                # FIXME: Include signal name, which should be in result.
                message += f"kill by signal {result.status.signum}"
            raise base.ProgramFailure(
                message,
                outputs =outputs,
                meta    =meta,
            )


    async def wait(self, run_id, proc):
        try:
            async for result in proc.results:
                if result is None:
                    # Not completed yet.
                    # FIXME: Do something with this!
                    pass
                else:
                    return self.__on_complete(proc, result)

        finally:
            # Clean up the process.
            try:
                await server.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")


    def reconnect(self, run_id, run_state):
        # FIXME
        raise NotImplementedError("reconnect")


    async def signal(self, run_id, run_state, signal):
        # FIXME
        raise NotImplementedError("signal")



