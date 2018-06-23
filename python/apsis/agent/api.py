import _posixsubprocess  # Yes, we use an internal API here.
import builtins
from   enum import Enum
import errno
import logging
import os
from   pathlib import Path
import sanic
import shlex
from   subprocess import SubprocessError

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

MAX_EXC_SIZE = 1048576

def start(argv, cwd, env, stdin_fd, out_fd):
    # Cribbed from subprocess.Popen._execute_child() (POSIX version).

    executable = argv[0]

    # For transferring possible exec failure from child to parent.
    # Data format: "exception name:hex errno:description"
    # Pickle is not used; it is complex and involves memory allocation.
    err_read, err_write = os.pipe()
    # err_write must not be in the standard io 0, 1, or 2 fd range.
    low_fds_to_close = []
    while err_write < 3:
        low_fds_to_close.append(err_write)
        err_write = os.dup(err_write)
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
                (err_write, ),          # pass_fds
                cwd, 
                env_list,
                stdin_fd,               # stdin read
                -1,                     # stdin write
                -1,                     # stdout read
                out_fd,                 # stdout write
                -1,                     # stderr read
                out_fd,                 # stderr write
                err_read, 
                err_write,
                True,                   # restore_signals
                True,                   # start_new_session
                None,                   # preexec_fn
            )
        finally:
            # be sure the FD is closed no matter what
            os.close(err_write)

        # Wait for exec to fail or succeed; possibly raising an exception.
        err_data = bytearray()
        while True:
            part = os.read(err_read, MAX_EXC_SIZE)
            err_data += part
            if not part or len(err_data) > MAX_EXC_SIZE:
                break

    finally:
        # Be sure the fd is closed no matter what.
        os.close(err_read)

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



#-------------------------------------------------------------------------------

class Process:

    WAIT_OPTIONS = os.WNOHANG | os.WUNTRACED | os.WCONTINUED

    def __init__(self, pid):
        self.__pid      = pid
        self.__state    = 0
        self.__status   = None
        self.__rusage   = None


    @property
    def pid(self):
        return self.__pid


    def wait(self):
        """
        Nonblocking wait.
        """
        if self.__state < 2:
            pid, status, rusage = os.wait4(self.__pid, self.WAIT_OPTIONS)
            if pid == 0:
                # Not done.
                pass
            elif pid == self.__pid:
                # Terminated.
                self.__state = 2
                self.__status = status
                self.__rusage = rusage
        else:
            # Already cleaned; do nothing.
            pass



class Process:

    STATE = Enum("STATE", ("INIT", "ERR", "RUN", "TERM", "DONE"))

    def __init__(self, dir, stdin):
        self.__state = self.STATE.INIT

        self.__dir = Path(os.mkdtemp(dir=dir))
        assert self.__dir.isdir()

        self.__exception    = None
        self.__pid          = None
        self.__stdin_path   = None
        self.__stdin_fd     = None
        self.__out_path     = None
        self.__out_fd       = None

        
    def start(self, argv, cwd, env, stdin):
        assert self.__state == self.STATE.INIT

        if stdin is None:
            # No stdin.
            self.__stdin_path = None
            self.__stdin_fd = -1
        else:
            # Write stdin to a file.
            self.__stdin_path = self.__dir / "stdin"
            with open(self.__stdin_path, "wb") as file:
                file.write(stdin)
            # Open the stdin file for the process to read.
            self.__stdin_fd = os.open(self.__stdin_path, os.O_RDONLY)
        
        # Open a file for the output.
        self.__out_path = self.__dir / "out"
        self.__out_fd = os.open(self.__out_path, os.O_CREAT | os.O_WRONLY)

        command = " ".join( shlex.quote(a) for a in argv )
        log.info(f"start: {self.__dir}: {command}")
        try:
            self.__pid = start(argv, cwd, env, self.__stdin_fd, self.__out_fd)
        except Exception as exc:
            log.info(f"start failed: {exc}")
            self.__state = self.STATE.ERR
            self.__exception = exc
        else:
            log.info(f"started: pid={self.__pid}")
            self.__state = self.STATE.RUN


    def sigchld(self):
        assert self.__state == self.STATE.RUN
        


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
    

