import _posixsubprocess  # Yes, we use an internal API here.
import builtins
import errno
import logging
import os
from   pathlib import Path
import sanic
from   subprocess import SubprocessError

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

MAX_EXC_SIZE = 1048576

def start(argv, cwd, env, stdin):
    # Cribbed from subprocess.Popen._execute_child() (POSIX version).

    # FIXME: Implement this.
    assert stdin is None

    executable = argv[0]

    # For transferring possible exec failure from child to parent.
    # Data format: "exception name:hex errno:description"
    # Pickle is not used; it is complex and involves memory allocation.
    errpipe_read, errpipe_write = os.pipe()
    # errpipe_write must not be in the standard io 0, 1, or 2 fd range.
    low_fds_to_close = []
    while errpipe_write < 3:
        low_fds_to_close.append(errpipe_write)
        errpipe_write = os.dup(errpipe_write)
    for low_fd in low_fds_to_close:
        os.close(low_fd)

    try:
        try:
            if env is not None:
                env_list = []
                for k, v in env.items():
                    k = os.fsencode(k)
                    if b'=' in k:
                        raise ValueError("illegal environment variable name")
                    env_list.append(k + b'=' + os.fsencode(v))
            else:
                # FIXME: What should the "default" environment be?
                env_list = None  # Use execv instead of execve.

            executables = (os.fsencode(executable), )
            pid = _posixsubprocess.fork_exec(
                argv, 
                executables,
                True,                   # close_fds
                (errpipe_write, ),      # pass_fds
                cwd, 
                env_list,
                -1,                     # stdin read
                -1,                     # stdin write
                -1,                     # stdout read
                -1,                     # stdout write
                -1,                     # stderr read
                -1,                     # stderr write
                errpipe_read, 
                errpipe_write,
                True,                   # restore_signals
                True,                   # start_new_session
                None,                   # preexec_fn
            )
        finally:
            # be sure the FD is closed no matter what
            os.close(errpipe_write)

        # Wait for exec to fail or succeed; possibly raising an exception.
        err_data = bytearray()
        while True:
            part = os.read(errpipe_read, MAX_EXC_SIZE)
            err_data += part
            if not part or len(err_data) > MAX_EXC_SIZE:
                break

    finally:
        # Be sure the fd is closed no matter what.
        os.close(errpipe_read)

    if len(err_data) > 0:
        try:
            exit_pid, status = os.waitpid(pid, 0)
            assert exit_pid == pid
            # FIXME: Do we care about the status?
            # return_code = convert_status(status)
        except ChildProcessError:
            # FIXME: Log something?
            pass

        try:
            exc_name, hex_errno, err_msg = err_data.split(b':', 2)
            exc_name    = exc_name.decode("ascii")
            errnum      = int(hex_errno, 16)
            err_msg     = err_msg.decode(errors="surrogatepass")
            exc_type    = getattr(builtins, exc_name, SubprocessError)
        except ValueError:
            exc_type, errnum, err_msg = (
                SubprocessError, 0,
                "Bad exception data from child: " + repr(err_data)
            )

        if issubclass(exc_type, OSError) and errnum != 0:
            noexec = err_msg == "noexec"
            if noexec:
                err_msg = ""
            if errnum != 0:
                err_msg = os.strerror(errnum)
                if errnum == errno.ENOENT:
                    if noexec:
                        # The error must be from chdir(cwd).
                        err_msg += ': ' + repr(cwd)
                    else:
                        err_msg += ': ' + repr(executable)
            raise exc_type(errnum, err_msg)
        raise exc_type(err_msg)
    
    else:
        return pid



class Processes:

    def __init__(self, dir: Path):
        self.__dir = dir


    def start(self, **kw_args):
        pid = start(**kw_args)
        return pid
        


#-------------------------------------------------------------------------------

def response_json(jso, status=200):
    return sanic.response.json(jso, status=status, indent=1, sort_keys=True)


API = sanic.Blueprint("v1")

@API.route("/processes", methods={"POST"})
async def processes_post(request):
    prog    = request.json["program"]
    argv    = prog["argv"]
    cwd     = Path(prog.get("cwd", "/")).absolute()
    # FIXME: env
    env     = None
    # FIXME: This needs to be a file.
    stdin   = prog.get("stdin", None)

    pid = start(argv, cwd, env, stdin)
    return response_json({
        "pid": pid,
    })
    

