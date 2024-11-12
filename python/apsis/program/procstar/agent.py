import asyncio
import logging
import procstar.spec
from   procstar.agent.exc import NoConnectionError, NoOpenConnectionInGroup, ProcessUnknownError
from   procstar.agent.proc import FdData, Interval, Result
import traceback
import uuid

from   apsis.lib import asyn
from   apsis.lib.json import check_schema
from   apsis.lib.parse import nparse_duration
from   apsis.lib.py import or_none, get_cfg
from   apsis.lib.sys import to_signal
from   apsis.procstar import get_agent_server
from   apsis.program import base
from   apsis.runs import join_args, template_expand

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

SUDO_ARGV_DEFAULT = ["/usr/bin/sudo", "--preserve-env", "--set-home"]

if_not_none = lambda k, v: {} if v is None else {k: v}

def _sudo_wrap(cfg, argv, sudo_user):
    if sudo_user is None:
        return argv
    else:
        sudo_argv = get_cfg(cfg, "procstar.agent.sudo.argv", SUDO_ARGV_DEFAULT)
        return [ str(a) for a in sudo_argv ] + [
            "--non-interactive",
            "--user", str(sudo_user),
            "--"
        ] + list(argv)


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
        "errors": res.errors,
    } | {
        k: dict(v.__dict__)
        for k in ("status", "times", "rusage", "proc_stat", "proc_statm", )
        if (v := getattr(res, k, None)) is not None
    }

    meta["procstar_proc_id"] = proc_id
    try:
        meta["procstar_conn"] = dict(res.procstar.conn.__dict__)
        meta["procstar_agent"] = dict(res.procstar.proc.__dict__)
    except AttributeError:
        pass

    return meta


def _combine_fd_data(old, new):
    if old is None:
        return new

    assert new.fd == old.fd
    assert new.encoding == old.encoding
    assert new.interval.stop - new.interval.start == len(new.data)
    # FIXME: Be more lenient?
    assert new.interval.start == old.interval.stop
    return FdData(
        fd      =old.fd,
        encoding=old.encoding,
        interval=Interval(old.interval.start, new.interval.stop),
        data    =old.data + new.data,
    )


async def _make_outputs(fd_data):
    """
    Constructs program outputs from combined output fd data.
    """
    if fd_data is None:
        return {}

    assert fd_data.fd == "stdout"
    assert fd_data.interval.start == 0
    assert fd_data.encoding is None

    output = fd_data.data
    length = fd_data.interval.stop
    return base.program_outputs(output, length=length, compression=None)


#-------------------------------------------------------------------------------

class BoundProcstarProgram(base.Program):

    def __init__(self, argv, *, group_id, sudo_user=None):
        self.__argv = [ str(a) for a in argv ]
        self.__group_id = str(group_id)
        self.__sudo_user = None if sudo_user is None else str(sudo_user)


    def __str__(self):
        return join_args(self.__argv)


    def to_jso(self):
        return super().to_jso() | {
            "argv"      : self.__argv,
            "group_id"  : self.__group_id,
        } | if_not_none("sudo_user", self.__sudo_user)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv        = pop("argv")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
            sudo_user   = pop("sudo_user", default=None)
        return cls(argv, group_id=group_id, sudo_user=sudo_user)


    def get_spec(self, cfg, *, run_id):
        """
        Returns the procstar proc spec for the program.
        """
        return procstar.spec.Proc(
            _sudo_wrap(cfg, self.__argv, self.__sudo_user),
            env=procstar.spec.Proc.Env(
                vars={
                    "APSIS_RUN_ID": run_id,
                },
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


    async def __delete(self, proc):
        try:
            # Request deletion.
            await proc.delete()
        except Exception as exc:
            # Just log this; from Apsis's standpoint, the proc is long done.
            log.error(f"delete {proc.proc_id}: {exc}")


    async def run(self, run_id, cfg):
        """
        Runs the program.

        Returns an async iterator of program updates.
        """
        server = get_agent_server()
        agent_cfg       = get_cfg(cfg, "procstar.agent", {})
        run_cfg         = get_cfg(agent_cfg, "run", {})
        conn_timeout    = get_cfg(agent_cfg, "connection.start_timeout", None)
        conn_timeout    = nparse_duration(conn_timeout)

        # Generate a proc ID.
        proc_id = str(uuid.uuid4())

        try:
            # Start the proc.
            proc, res = await server.start(
                proc_id     =proc_id,
                group_id    =self.__group_id,
                spec        =self.get_spec(cfg, run_id=run_id),
                conn_timeout=conn_timeout,
            )

        except NoOpenConnectionInGroup as exc:
            log.warning(str(exc))
            yield base.ProgramError(f"procstar: {exc}")

        except Exception as exc:
            log.error(f"procstar: {traceback.format_exc()}")
            yield base.ProgramError(f"procstar: {exc}")

        else:
            run_state = {
                "conn_id": proc.conn_id,
                "proc_id": proc_id,
            }
            yield base.ProgramRunning(
                run_state,
                meta=_make_metadata(proc_id, res)
            )

            # Hand off to __finish.
            async for update in self.__finish(proc, res, run_cfg):
                yield update


    async def connect(self, run_id, run_state, cfg):
        server = get_agent_server()
        agent_cfg = get_cfg(cfg, "procstar.agent", {})
        run_cfg = get_cfg(agent_cfg, "run", {})

        conn_id = run_state["conn_id"]
        proc_id = run_state["proc_id"]

        try:
            conn_timeout = nparse_duration(
                get_cfg(agent_cfg, "connection.reconnect_timeout", None))

            log.info(f"reconnecting: {proc_id} on conn {conn_id}")
            proc = await server.reconnect(
                conn_id     =conn_id,
                proc_id     =proc_id,
                conn_timeout=conn_timeout,
            )

            # Request a result immediately.
            await proc.request_result()

        except NoConnectionError as exc:
            msg = f"reconnect failed: {proc_id}: {exc}"
            log.error(msg)
            yield base.ProgramError(msg)

        else:
            log.info(f"reconnected: {proc_id} on conn {conn_id}")
            # Hand off to __finish.
            async for update in self.__finish(proc, None, run_cfg):
                yield update


    async def __finish(self, proc, res, run_cfg):
        """
        Handles running `proc` until termination.

        :param res:
          The most recent `Result`, if any.
        """
        proc_id = proc.proc_id
        tasks = asyn.TaskGroup()

        try:
            # Output collected so far.
            fd_data = None

            # Start tasks to request periodic updates of results and output.
            update_interval = nparse_duration(run_cfg.get("update_interval", None))
            output_interval = nparse_duration(run_cfg.get("output_interval", None))

            if update_interval is not None:
                # Start a task that periodically requests the current result.
                tasks.add(
                    "poll update",
                    asyn.poll(proc.request_result, update_interval)
                )

            if output_interval is not None:
                # Start a task that periodically requests additional output.
                def more_output():
                    # From the current position to the end.
                    start = 0 if fd_data is None else fd_data.interval.stop
                    interval = Interval(start, None)
                    return proc.request_fd_data("stdout", interval=interval)

                tasks.add("poll output", asyn.poll(more_output, output_interval))

            # Process further updates, until the process terminates.
            async for update in proc.updates:
                match update:
                    case FdData():
                        fd_data = _combine_fd_data(fd_data, update)
                        yield base.ProgramUpdate(outputs=await _make_outputs(fd_data))

                    case Result() as res:
                        meta = _make_metadata(proc_id, res)

                        if res.state == "running":
                            # Intermediate result.
                            yield base.ProgramUpdate(meta=meta)
                        else:
                            # Process terminated.
                            break

            else:
                # Proc was deleted--but we didn't delete it.
                assert False, "proc deleted"

            # Stop update tasks.
            await tasks.cancel_all()

            # Do we have the complete output?
            length = res.fds.stdout.length
            if length > 0 and (
                    fd_data is None
                    or fd_data.interval.stop < length
            ):
                # Request any remaining output.
                await proc.request_fd_data(
                    "stdout",
                    interval=Interval(
                        0 if fd_data is None else fd_data.interval.stop,
                        None
                    )
                )
                # Wait for it.
                async for update in proc.updates:
                    match update:
                        case FdData():
                            fd_data = _combine_fd_data(fd_data, update)
                            # Confirm that we've accumulated all the output as
                            # specified in the result.
                            assert fd_data.interval.start == 0
                            assert fd_data.interval.stop == res.fds.stdout.length
                            break

                        case _:
                            log.debug("expected final FdData")

            outputs = await _make_outputs(fd_data)

            if res.status.exit_code == 0:
                # The process terminated successfully.
                yield base.ProgramSuccess(meta=meta, outputs=outputs)
            else:
                # The process terminated unsuccessfully.
                exit_code = res.status.exit_code
                signal = res.status.signal
                cause = (
                    f"exit code {exit_code}" if signal is None
                    else f"killed by {signal}"
                )
                yield base.ProgramFailure(cause, meta=meta, outputs=outputs)

        except asyncio.CancelledError:
            # Don't clean up the proc; we can reconnect.
            proc = None

        except ProcessUnknownError:
            # Don't ask to clean it up; it's already gone.
            proc = None

        except Exception as exc:
            log.error(f"procstar: {traceback.format_exc()}")

            yield base.ProgramError(
                f"procstar: {exc}",
                meta=(
                    _make_metadata(proc_id, res)
                    if proc is not None and res is not None
                    else {}
                )
            )

        finally:
            # Cancel our helper tasks.
            await tasks.cancel_all()
            if proc is not None:
                # Giving up on this proc; ask the agent to delete it.
                await self.__delete(proc)


    async def signal(self, run_id, run_state, signal):
        server = get_agent_server()

        signal = to_signal(signal)
        log.info(f"sending signal: {run_id}: {signal}")

        proc_id = run_state["proc_id"]
        try:
            proc = server.processes[proc_id]
        except KeyError:
            raise ValueError(f"no process: {proc_id}")
        await proc.send_signal(int(signal))



#-------------------------------------------------------------------------------

class ProcstarProgram(base.Program):

    def __init__(
            self, argv, *,
            group_id    =procstar.proto.DEFAULT_GROUP,
            sudo_user   =None
    ):
        self.__argv         = [ str(a) for a in argv ]
        self.__group_id     = str(group_id)
        self.__sudo_user    = None if sudo_user is None else str(sudo_user)


    def __str__(self):
        return join_args(self.__argv)


    def bind(self, args):
        argv        = tuple( template_expand(a, args) for a in self.__argv )
        group_id    = or_none(template_expand)(self.__group_id, args)
        sudo_user   = or_none(template_expand)(self.__sudo_user, args)
        return BoundProcstarProgram(
            argv, group_id=group_id, sudo_user=sudo_user)


    def to_jso(self):
        return super().to_jso() | {
            "argv"      : self.__argv,
            "group_id"  : self.__group_id,
        } | if_not_none("sudo_user", self.__sudo_user)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            argv        = pop("argv")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
            sudo_user   = pop("sudo_user", default=None)
        return cls(argv, group_id=group_id, sudo_user=sudo_user)



#-------------------------------------------------------------------------------

class ProcstarShellProgram(base.Program):

    SHELL = "/usr/bin/bash"

    def __init__(
            self, command, *,
            group_id    =procstar.proto.DEFAULT_GROUP,
            sudo_user   =None,
    ):
        self.__command      = str(command)
        self.__group_id     = str(group_id)
        self.__sudo_user    = None if sudo_user is None else str(sudo_user)


    def bind(self, args):
        argv        = [self.SHELL, "-c", template_expand(self.__command, args)]
        group_id    = or_none(template_expand)(self.__group_id, args)
        sudo_user   = or_none(template_expand)(self.__sudo_user, args)
        return BoundProcstarProgram(argv, group_id=group_id, sudo_user=sudo_user)


    def to_jso(self):
        return super().to_jso() | {
            "command"   : self.__command,
            "group_id"  : self.__group_id,
        } | if_not_none("sudo_user", self.__sudo_user)


    @classmethod
    def from_jso(cls, jso):
        with check_schema(jso) as pop:
            command     = pop("command")
            group_id    = pop("group_id", default=procstar.proto.DEFAULT_GROUP)
            sudo_user   = pop("sudo_user", default=None)
        return cls(command, group_id=group_id, sudo_user=sudo_user)



