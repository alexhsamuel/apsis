import asyncio
import logging
from   procstar import proto
import procstar.spec
from   procstar.agent.exc import NoConnectionError
from   procstar.agent.proc import FdData, Result
import procstar.agent.server
import time
import traceback
import uuid

from   apsis.lib import asyn
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

def _make_metadata(proc_id, res: dict):
    """
    Extracts run metadata from a proc result message.

    - `status`: Process raw status (see `man 2 wait`) and decoded exit code
      and signal info.

    - `times`: Process timing from the Procstar agent on the host running the
      program.  `elapsed` is computed from a monotonic clock.

    - `rusage`: Process resource usage.  See `man 2 getrusage` for details.

    - `proc_stat`: Process information collected from `/proc/<pid>/stat`.  See
      the `proc(5)` man page for details.

    - `proc_statm`: Process memory use collected from `/proc/<pid>/statm`.  See
      the `proc(5)` man page for details.

    - `proc_id`: The Procstar process ID.

    - `conn`: Connection info the the Procstar agent.

    - `procstar_proc`: Process information about the Procstar agent itself.

    """
    meta = {
        k: v
        for k in ("status", "errors", "times", "rusage", "proc_stat", "proc_statm", )
        if (v := res.get(k))
    }

    meta["proc_id"] = proc_id
    try:
        meta["conn"] = dict(res["procstar"].conn.__dict__)
        meta["procstar_proc"] = dict(res["procstar"].proc.__dict__)
    except AttributeError:
        pass

    return meta


def _make_outputs(fd_data):
    assert fd_data.fd == "stdout"
    assert fd_data.interval.start == 0  # FIXME: For now.
    assert fd_data.encoding is None
    return base.program_outputs(fd_data.data, length=fd_data.interval.stop)


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


    @property
    def spec(self):
        """
        The procstar proc spec for the program.
        """
        return procstar.spec.Proc(
            self.__argv,
            env=procstar.spec.Proc.Env(
                # Inherit the entire environment from procstar, since it probably
                # includes important configuration.
                inherit=True,
            ),
            fds={
                # Capture stdout to a temporary file.
                "stdout": procstar.spec.Proc.Fd.Capture(
                    "tempfile",
                    encoding=None,
                    # Don't attach output to results, so we can poll quickly.
                    attached=False,
                ),
                # Merge stderr into stdin.
                "stderr": procstar.spec.Proc.Fd.Dup(1),
            },
        )


    async def run(self, run_id, cfg):
        """
        Runs the program.

        Returns an async iterator of program updates.
        """
        # FIXME
        result_interval = 11
        output_interval = 5

        assert SERVER is not None
        proc = None
        tasks = asyn.TaskGroup()

        # Generate a proc ID.
        proc_id = str(uuid.uuid4())

        # Track the most recent proc result and output data we've received.
        res = None
        fd_data = None

        try:
            # Start the proc.
            proc = await SERVER.start(
                proc_id     =proc_id,
                group_id    =self.__group_id,
                spec        =self.spec,
                conn_timeout=SERVER.start_timeout,  # FIXME
            )

            # Wait for the first result to arrive.
            result = await anext(proc.updates)
            assert isinstance(result, Result), "expected initial result"
            # Unpack Procstar's result dict.
            res = result.res

            run_state = {
                "conn_id": proc.conn_id,
                "proc_id": proc_id,
            }
            yield base.ProgramRunning(
                run_state,
                meta=_make_metadata(proc_id, res)
            )

            # Start tasks to request periodic updates of results and output.
            tasks.add(
                "poll result",
                asyn.poll(proc.request_result, result_interval)
            )
            tasks.add(
                "poll output",
                asyn.poll(
                    lambda: proc.request_fd_data("stdout"),  # FIXME: From start for now only.
                    output_interval
                )
            )

            # Process further updates, until the process terminates.
            async for update in proc.updates:
                match update:
                    case FdData() as fd_data:
                        yield base.ProgramUpdate(outputs=_make_outputs(fd_data))

                    case Result(res):
                        meta = _make_metadata(proc_id, res)

                        if res["state"] == "running":
                            # Intermediate result.
                            yield base.ProgramUpdate(meta=meta)
                        else:
                            # Process terminated.
                            break

            else:
                # Proc was deleted-- but we didn't delete it.
                assert False, "proc deleted"

            # Stop update tasks.
            await tasks.cancel_all()

            # Do we have the complete output?
            length = res["fds"]["stdout"]["length"]
            if length > 0 and (
                    fd_data is None
                    or fd_data.interval.stop < length
            ):
                # Request the complete output.
                await proc.request_fd_data("stdout")  # FIXME: From the start for now only.
                # Wait for it.
                async for update in proc.updates:
                    match update:
                        case FdData() as fd_data:
                            assert fd_data.interval.stop == length
                            outputs = _make_outputs(fd_data)
                            break

                        case _:
                            log.debug("expected final FdData")

            else:
                # No further output update.
                outputs = None

            status = res["status"]
            if status["exit_code"] == 0:
                # The process terminated successfully.
                yield base.ProgramSuccess(meta=meta, outputs=outputs)
            else:
                # The process terminated unsuccessfully.
                cause = (
                    f"exit code {status['exit_code']}"
                    if status.signal is None
                    else f"killed by {status['signal']}"
                )
                yield base.ProgramFailure(cause, meta=meta, outputs=outputs)

        except asyncio.CancelledError:
            # Don't clean up the proc; we can reconnect.
            proc = None

        except Exception as exc:
            log.error(f"procstar: {traceback.format_exc()}")
            yield base.ProgramError(
                f"procstar: {exc}",
                meta=(
                    _make_metadata(proc_id, res)
                    if proc is not None and res is not None
                    else None
                )
            )

        finally:
            await tasks.cancel_all()
            if proc is not None:
                try:
                    await proc.delete()
                    # Process remaining updates until the proc is deleted.
                    async for update in proc.updates:
                        pass
                except Exception as exc:
                    log.error(f"delete {proc_id}: {exc}")


    async def __finish_old(self, run_id, proc):
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
                    meta    = _make_metadata(proc.proc_id, proc.results.latest)
                    output  = proc.results.latest.fds.stdout.text.encode()
                    outputs = base.program_outputs(output)
                log.warning(f"no result update in {TIMEOUT} s: {run_id}")
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
                    log.warning(f"no connection to agent: {run_id}")
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
                meta    = _make_metadata(proc.proc_id, result)
                yield base.ProgramUpdate(meta=meta, outputs=outputs)
                continue

            # Completed.  Finish up this run.
            meta = _make_metadata(proc.proc_id, result)

            # Request the full output.
            await conn.send(proto.ProcFdDataRequest(proc.proc_id, "stdout"))

            # Collect output.
            output, encoding = await proc.results.get_fd_res("stdout")
            assert isinstance(output, bytes)
            assert encoding is None
            outputs = base.program_outputs(output)

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
        try:
            proc = SERVER.processes[proc_id]
        except KeyError:
            raise ValueError(f"no process: {proc_id}")
        await proc.send_signal(proc_id, int(signal))



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



