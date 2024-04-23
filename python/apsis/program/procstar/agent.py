import asyncio
import logging
from   procstar import proto
import procstar.spec
from   procstar.agent.exc import NoConnectionError
import procstar.agent.server
import time
import uuid

from   apsis.lib.json import check_schema
from   apsis.lib.parse import parse_duration
from   apsis.lib.py import or_none
from   apsis.lib.sys import to_signal
from   apsis.program import base
from   apsis.runs import join_args, template_expand

log = logging.getLogger(__name__)

# The websockets library is too chatty at DEBUG (but remove this for debugging
# low-level WS or TLS problems).
logging.getLogger("websockets.server").setLevel(logging.INFO)

#-------------------------------------------------------------------------------

def _get_metadata(proc_id, result):
    """
    Extracts run metadata from a proc result message.

    - `status`: Process raw status (see `man 2 wait`) and decoded exit code
      and signal info.

    - `times`: Process timing from the Procstar agent on the host running the
      program.  `elapsed` is computed from a monotonic clock.

    - `rusage`: Process resource usage.  See `man 2 getrusage` for details.

    - `proc_stat`: Process information collected from `/proc/<pid>/stat`.  See
      `man 5 proc` for details.

    - `proc_statm`: Process memory use collected from `/proc/<pid>/statm`.  See
      `man 5 proc` for details.

    - `proc_id`: The Procstar process ID.

    - `conn`: Connection info the the Procstar agent.

    - `procstar_proc`: Process information about the Procstar agent itself.

    """
    meta = {
        k: v
        for k in ("errors", )
        if (v := getattr(result, k, None))
    } | {
        k: dict(v.__dict__)
        for k in ("status", "times", "rusage", "proc_stat", "proc_statm", )
        if (v := getattr(result, k, None))
    }

    meta["proc_id"] = proc_id
    try:
        meta["conn"] = dict(result.procstar.conn.__dict__)
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
    assert SERVER is None, "server already created"

    # Network stuff.
    FROM_ENV        = procstar.agent.server.FROM_ENV
    server_cfg      = cfg.get("server", {})
    host            = server_cfg.get("host", FROM_ENV)
    port            = server_cfg.get("port", FROM_ENV)
    access_token    = server_cfg.get("access_token", FROM_ENV)
    tls_cfg         = server_cfg.get("tls", {})
    cert_path       = tls_cfg.get("cert_path", FROM_ENV)
    key_path        = tls_cfg.get("key_path", FROM_ENV)

    # Group config.
    conn_cfg        = cfg.get("connection", {})
    start_timeout   = parse_duration(conn_cfg.get("start_timeout", "0"))
    rec_timeout     = parse_duration(conn_cfg.get("reconnect_timeout", "0"))
    update_interval = parse_duration(conn_cfg.get("update_interval", "0"))

    SERVER = procstar.agent.server.Server()
    SERVER.start_timeout = start_timeout
    SERVER.reconnect_timeout = rec_timeout
    SERVER.update_interval = update_interval

    return SERVER.run_forever(
        host        =host,
        port        =port,
        tls_cert    =FROM_ENV if cert_path is FROM_ENV else (cert_path, key_path),
        access_token=access_token,
    )


#-------------------------------------------------------------------------------

class BoundProcstarProgram(base.Program):

    def __init__(self, argv, *, group_id):
        self.__argv = [ str(a) for a in argv ]
        self.__group_id = str(group_id)


    def __str__(self):
        return join_args(self.__argv)


    def to_jso(self):
        return super().to_jso() | {
            "argv"      : self.__argv,
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


    async def run(self, run_id, cfg):
        assert SERVER is not None

        proc_id = str(uuid.uuid4())
        spec = self.__make_spec()

        try:
            proc = await SERVER.start(
                proc_id,
                spec,
                group_id    =self.__group_id,
                conn_timeout=SERVER.start_timeout,
            )
        except Exception as exc:
            yield base.ProgramError(f"procstar: {exc}")
            return

        try:
            # Wait for the first result.
            try:
                result = await anext(proc.results)

            except Exception as exc:
                yield base.ProgramError(str(exc))

            else:
                meta = _get_metadata(proc.proc_id, result)

                if result.state == "error":
                    yield base.ProgramError(
                        "; ".join(result.errors),
                        meta=meta,
                    )

                elif result.state in {"running", "terminated"}:
                    # If immediately receive a result with state "terminated",
                    # we must have missed the previous running result.
                    conn_id = result.procstar.conn.conn_id
                    run_state = {"conn_id": conn_id, "proc_id": proc_id}
                    yield base.ProgramRunning(run_state, meta=meta)

                    async for update in self.__finish(run_id, proc):
                        yield update

                else:
                    # We should not immediately receive a result with state
                    # "terminated".
                    yield base.ProgramError(
                        f"unexpected proc state: {result.state}",
                        meta=meta,
                    )

        except asyncio.CancelledError:
            pass

        else:
            try:
                await SERVER.delete(proc.proc_id)
            except Exception as exc:
                log.error(f"delete {proc.proc_id}: {exc}")


    async def __finish(self, run_id, proc):
        # Timeout to receive a result update from the agent, before marking the
        # run as error.
        # FIXME: This is temporary, until we handle WebSocket connection and
        # disconnection, and aging out of connections, properly.
        TIMEOUT = 129600

        conn = SERVER.connections[proc.conn_id]
        last_result_time = time.monotonic()

        while True:
            # How far are we from timing out?
            timeout = last_result_time + TIMEOUT - time.monotonic()
            if timeout < 0:
                # We haven't received a result in too long, so mark the run as
                # error.  Use output and metadata from the most recent results,
                # if available.
                if proc.results.latest is None:
                    meta = outputs = None
                else:
                    meta    = _get_metadata(proc.proc_id, proc.results.latest)
                    output  = proc.results.latest.fds.stdout.text.encode()
                    outputs = base.program_outputs(output)
                logging.warning(f"no result update in {TIMEOUT} s: {run_id}")
                yield base.ProgramError(
                    f"lost Procstar process after {TIMEOUT} s",
                    outputs =outputs,
                    meta    =meta,
                )

            # Wait for the next result from the agent, no more that update_interval.
            wait_timeout = (
                min(timeout, SERVER.update_interval) if SERVER.update_interval > 0
                else timeout
            )
            try:
                # Unless the proc is already terminated, await the next message.
                result = (
                    proc.results.latest
                    if proc.results.latest is not None
                    and proc.results.latest.state == "terminated"
                    else await asyncio.wait_for(anext(proc.results), wait_timeout)
                )
            except asyncio.TimeoutError:
                # Didn't receive a result.
                if conn.open:
                    # Request an update.
                    # FIXME: There should be an API!
                    await conn.send(proto.ProcResultRequest(proc.proc_id))
                else:
                    # Can't request an update; the agent is not connected.
                    logging.warning(f"no connection to agent: {run_id}")
                continue
            except Exception as exc:
                yield base.ProgramError(f"procstar: {exc}")
            else:
                # Received a result update.  Reset the timeout clock.
                last_result_time = time.monotonic()

            if result.state == "running":
                # Not completed yet.  Collect results.
                # FIXME: Output should be incremental.
                output  = result.fds.stdout.text.encode()
                outputs = base.program_outputs(output)
                meta    = _get_metadata(proc.proc_id, result)
                yield base.ProgramUpdate(meta=meta, outputs=outputs)
                continue

            # Collect results.
            outputs = base.program_outputs(
                b"" if result.fds.stdout is None
                else result.fds.stdout.text.encode()
            )
            meta    = _get_metadata(proc.proc_id, result)

            if result.state == "error":
                # The process failed to start on the agent.
                yield base.ProgramError(
                    "; ".join(result.errors),
                    outputs =outputs,
                    meta    =meta,
                )

            elif result.state == "terminated":
                # The process ran on the agent.
                status = result.status
                if status.exit_code == 0:
                    # The process completed successfully.
                    yield base.ProgramSuccess(
                        outputs =outputs,
                        meta    =meta,
                    )

                else:
                    # The process terminated unsuccessfully.
                    cause = (
                        f"exit code {status.exit_code}"
                        if status.signal is None
                        else f"killed by {status.signal}"
                    )
                    yield base.ProgramFailure(
                        str(cause),
                        outputs =outputs,
                        meta    =meta,
                    )

            else:
                assert False, f"unknown proc state: {result.state}"

            break



    async def connect(self, run_id, run_state, cfg):
        assert SERVER is not None

        conn_id = run_state["conn_id"]
        proc_id = run_state["proc_id"]

        try:
            log.info(f"reconnecting: {proc_id} on conn {conn_id}")
            proc = await SERVER.reconnect(
                conn_id,
                proc_id,
                conn_timeout=SERVER.reconnect_timeout,
            )

        except NoConnectionError as exc:
            msg = f"reconnect failed: {proc_id}: {exc}"
            log.error(msg)
            yield base.ProgramError(msg)

        else:
            log.info(f"reconnected: {proc_id} on conn {conn_id}")
            async for update in self.__finish(run_id, proc):
                yield update

        finally:
            try:
                await SERVER.delete(proc_id)
            except Exception as exc:
                log.error(f"delete {proc_id}: {exc}")
            raise


    async def signal(self, run_id, run_state, signal):
        signal = to_signal(signal)
        log.info(f"sending signal: {run_id}: {signal}")
        proc_id = run_state["proc_id"]
        await SERVER.send_signal(proc_id, int(signal))



#-------------------------------------------------------------------------------

class ProcstarProgram(base.Program):

    def __init__(self, argv, *, group_id=procstar.proto.DEFAULT_GROUP):
        self.__argv = [ str(a) for a in argv ]
        self.__group_id = group_id


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv        = tuple( template_expand(a, args) for a in self.__argv )
        group_id    = or_none(template_expand)(self.__group_id, args)
        return BoundProcstarProgram(argv, group_id=group_id)


    def to_jso(self):
        return super().to_jso() | {
            "argv"      : self.__argv,
            "group_id"  : self.__group_id,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv        = pop("argv")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
        return cls(argv, group_id=group_id)



#-------------------------------------------------------------------------------

class ProcstarShellProgram(base.Program):

    SHELL = "/usr/bin/bash"

    def __init__(self, command, *, group_id=procstar.proto.DEFAULT_GROUP):
        self.__command = str(command)
        self.__group_id = str(group_id)


    def bind(self, args):
        argv        = [self.SHELL, "-c", template_expand(self.__command, args)]
        group_id    = or_none(template_expand)(self.__group_id, args)
        return BoundProcstarProgram(argv, group_id=group_id)


    def to_jso(self):
        return super().to_jso() | {
            "command"   : self.__command,
            "group_id"  : self.__group_id,
        }


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            command     = pop("command")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
        return cls(command, group_id=group_id)



