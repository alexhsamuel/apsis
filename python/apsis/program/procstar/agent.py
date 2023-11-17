import logging
import procstar.spec
import procstar.agent.server
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


#-------------------------------------------------------------------------------

SERVER = None

def start_server(cfg):
    """
    Creates and configures the global agent server.

    :return:
      Awaitable that runs the server.
    """
    global SERVER
    assert SERVER is None

    server_cfg  = cfg.get("server", {})
    tls_cfg     = server_cfg.get("tls", {})
    FROM_ENV    = procstar.agent.server.FROM_ENV

    host            = server_cfg.get("host", FROM_ENV)
    port            = server_cfg.get("port", FROM_ENV)
    access_token    = server_cfg.get("access_token", FROM_ENV)
    cert_path       = tls_cfg.get("cert_path", FROM_ENV)
    key_path        = tls_cfg.get("key_path", FROM_ENV)

    SERVER = procstar.agent.server.Server()
    return SERVER.run_forever(
        host        =host,
        port        =port,
        tls_cert    =(cert_path, key_path),
        access_token=access_token,
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


    def __make_spec(self):
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
        assert SERVER is not None

        proc_id = str(uuid.uuid4())
        # FIXME: Handle NoOpenConnectionInGroup and wait.
        try:
            proc = await SERVER.start(
                proc_id,
                self.__make_spec(),
                group_id=self.__group_id,
            )
        except Exception as exc:
            raise base.ProgramError(f"procstar: {exc}")

        # Wait for the first result.
        try:
            try:
                result = await anext(proc.results)

            except Exception as exc:
                raise base.ProgramError(str(exc))

            else:
                meta = _get_metadata(result)

                if result.state == "error":
                    raise base.ProgramError(
                        "; ".join(result.errors),
                        meta=meta,
                    )

                elif result.state == "running":
                    conn_id = result.procstar.conn.conn_id
                    run_state = {"conn_id": conn_id, "proc_id": proc_id}
                    done = self.__wait(run_id, proc)
                    return base.ProgramRunning(run_state, meta=meta), done

                else:
                    # We should not immediately receive a result with state
                    # "terminated".
                    raise base.ProgramError(
                        f"unexpected proc state: {result.state}",
                        meta=meta,
                    )

        except base.ProgramError:
            # Clean up the process, if it's not running.
            try:
                await SERVER.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")
            raise


    def __on_result(self, result):
        output = result.fds.stdout.text.encode()
        outputs = base.program_outputs(output)
        meta = _get_metadata(result)

        if result.state == "error":
            raise base.ProgramError(
                "; ".join(result.errors),
                outputs =outputs,
                meta    =meta,
            )

        elif result.state == "running":
            # Not completed yet.
            # FIXME: Do something with this!
            return None

        elif result.state == "terminated":
            if result.status.exit_code == 0:
                return base.ProgramSuccess(
                    outputs =outputs,
                    meta    =meta,
                )

            else:
                if result.status.signal is not None:
                    cause = f"killed by {result.status.signal}"
                else:
                    cause = f"exit code {result.status.exit_code}"
                raise base.ProgramFailure(
                    f"program failed: {cause}",
                    outputs =outputs,
                    meta    =meta,
                )

        else:
            assert False, f"unknown proc state: {result.state}"


    async def __wait(self, run_id, proc):
        try:
            async for result in proc.results:
                if (success := self.__on_result(result)) is not None:
                    return success

        finally:
            # Clean up the process.
            try:
                await SERVER.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")


    def reconnect(self, run_id, run_state):
        assert SERVER is not None

        # FIXME
        raise NotImplementedError("reconnect")


    async def signal(self, run_id, run_state, signal):
        # FIXME
        raise NotImplementedError("signal")



