#!/usr/bin/env python3

"""
- "argv": An array of strings containing the argument vector.  The first element
  is the path to the executable to run.  If this is not an absolute path, PATH
  is used to find it.  Additional strings are passed as arguments.  

- "cmd": A string containing the bash command or program to run.  

- "cwd": The initial CWD for the program.  If null, the initial CWD is
  unspecified.

- "combine_stderr": If true, merge stderr with stdout.  Otherwise, capture
  stderr separately.


- "host": The name of the host to run on.  If `None`, runs on the current host.

- "user": The user to run as.  If `None`, runs as the current user.

- "strategy": 


Exactly one of "argv" or "cmd" must be specified.
"""


# TODO:
# - specify prog dir location
# - specify env whitelist
# - stdin support
# - push result to webhook
# - clean up the prog dir


import _posixsubprocess
import argparse
import builtins
import datetime
import errno
import json
import os
import pathlib
import shlex
import shutil
import signal
import subprocess
import tempfile

#-------------------------------------------------------------------------------

ENV_WHITELIST = (
    "HOME",
    "LANG",
    "LOGNAME",
    "SHELL",
    "TMPDIR",
    "USER",
)


class ProgramSpecError(RuntimeError):

    pass



def interpret_status(status):
    """
    Splits the exit status into return code or signal name.

    :return:
      Return code, signal name.
    """
    return (
        os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
        signal.Signals(os.WTERMSIG(status)).name if os.WIFSIGNALED(status) 
        else None
    )


def rusage_to_dict(rusage):
    usage = { 
        n: getattr(rusage, n) 
        for n in dir(rusage)
        if n.startswith("ru_")
    }
    # Round times to ns, to avoid silly rounding issues.
    return {
        n: round(v, 9) if isinstance(v, float) else v
        for n, v in usage.items()
    }


#-------------------------------------------------------------------------------

def fork_exec(argv, cwd, env, stdin_fd, stdout_fd, stderr_fd):
    """
    Starts a program in a subprocess.

    :param cwd:
      Process initial CWD.
    :param env:
      Process environment, or `None` for current.
    :raise FileNotFoundError:
      The executable was not found.
    :raise PermissionError:
      The executable could not be run.
    """
    MAX_EXC_SIZE = 1048576

    argv = [ str(a) for a in argv ]
    executable = argv[0]
    cwd = str(cwd)

    # Logic copied from subprocess.Popen._execute_child() (POSIX version).

    # Pipe for transferring exec failure from child to parent, in format
    # "exception name:hex errno:description".
    err_read, err_write = os.pipe()
    assert err_write >= 3

    try:
        try:
            if env is not None:
                env_list = []
                for k, v in env.items():
                    k = os.fsencode(k)
                    if b'=' in k:
                        raise ValueError("illegal environment variable name")
                    env_list.append(k + b'=' + os.fsencode(str(v)))
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
                stdout_fd,              # stdout write
                -1,                     # stderr read
                stderr_fd,              # stderr write
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
        except ChildProcessError:
            # FIXME: Log something?
            pass

        try:
            exc_name, hex_errno, err_msg = err_data.split(b':', 2)
            exc_name    = exc_name.decode("ascii")
            errnum      = int(hex_errno, 16)
            err_msg     = err_msg.decode(errors="surrogatepass")
            exc_type    = getattr(
                builtins, exc_name, subprocess.SubprocessError)
        except ValueError:
            exc_type, errnum, err_msg = (
                subprocess.SubprocessError, 0,
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


def set_up(prog):
    try:
        # The shell command to run.
        cmd = prog["cmd"]
    except KeyError:
        try:
            argv = prog["argv"]
        except KeyError:
            raise ProgramSpecError("neither cmd nor argv given")
        else:
            cmd = "exec " + " ".join( shlex.quote(a) for a in argv )
    else:
        if "argv" in prog:
            raise ProgramSpecError("both cmd and argv given")

    user = prog.get("user", None)
    host = prog.get("host", None)

    if user is not None:
        raise NotImplemented("other user")

    if host is None:
        # Invoke the command in a fresh login shell.
        argv = ["/bin/bash", "-l", "-c", cmd]

        # Whitelist standard environment variables.
        env = {
            v: os.environ[v]
            for v in ENV_WHITELIST
            if v in os.environ
        }

    else:
        # Remote case.
        raise NotImplemented("remote host")

    cwd = str(prog.get("cwd", "/"))

    return argv, cwd, env


class ProgDir:

    def __init__(self, prog):
        combine_stderr      = prog.get("combine_stderr", False)
        self.path           = pathlib.Path(tempfile.mkdtemp(prefix="honcho-"))
        self.stdout_path    = self.path / "stdout"
        self.stderr_path    = None if combine_stderr else self.path / "stderr"
        self.prog_path      = self.path / "prog.json"
        self.log_path       = self.path / "log"

        with open(self.prog_path, "w") as file:
            json.dump(prog, file, indent=2)

        self.__log_file = open(self.log_path, "w")
        self.log("created")


    def to_jso(self):
        return {
            "path"          : str(self.path),
            "stdout_path"   : str(self.stdout_path),
            "stderr_path"   : str(self.stderr_path),
            "prog_path"     : str(self.prog_path),
            "log_path"      : str(self.log_path),
        }


    def log(self, message):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(f"{timestamp} {message}", file=self.__log_file)
        self.__log_file.flush()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc, exc_tb):
        self.clean()


    def clean(self):
        """
        Cleans up.
        """
        self.__log_file.close()
        shutil.rmtree(self.path)


    def get_stdout(self) -> bytes:
        with open(self.stdout_path, "rb") as file:
            return file.read()


    def get_stderr(self) -> bytes:
        with open(self.stderr_path, "rb") as file:
            return file.read()




class Running:

    def __init__(self, argv, env, cwd, pid):
        self.argv           = argv
        self.env            = env
        self.cwd            = cwd
        self.pid            = pid


    def to_jso(self):
        return {
            "argv"          : self.argv,
            "env"           : self.env,
            "cwd"           : self.cwd,
            "honcho_pid"    : os.getpid(),
            "pid"           : self.pid,
        }



def start(prog, prog_dir) -> Running:
    argv, cwd, env  = set_up(prog)
    combine_stderr  = bool(prog.get("combine_stderr", False))

    stdin_fd  = os.open("/dev/null", os.O_RDONLY)
    assert stdin_fd >= 0

    stdout_fd = os.open(
        prog_dir.stdout_path, os.O_CREAT | os.O_WRONLY, mode=0o600)
    assert stdout_fd >= 0
    stderr_fd = (
        stdout_fd if combine_stderr
        else os.open(prog_dir.stderr_path, os.O_CREAT | os.O_WRONLY, mode=0o600)
    )
    assert stderr_fd >= 0

    pid = fork_exec(argv, cwd, env, stdin_fd, stdout_fd, stderr_fd)
    os.close(stdout_fd)
    os.close(stderr_fd)
    prog_dir.log(f"started with pid {pid}")

    return Running(argv, env, cwd, pid)


class Result:
    """
    Result of a terminated process.
    """

    def __init__(self, running, status, rusage):
        # Decode system things here, as they may be different on other hosts.
        return_code, signal_name = interpret_status(status)
        rusage = rusage_to_dict(rusage)

        self.argv           = running.argv
        self.env            = running.env
        self.cwd            = running.cwd
        self.pid            = running.pid
        self.status         = status
        self.return_code    = return_code
        self.signal_name    = signal_name
        self.rusage         = rusage


    def to_jso(self):
        return {
            "argv"          : self.argv,
            "env"           : self.env,
            "cwd"           : self.cwd,
            "honcho_pid"    : os.getpid(),
            "pid"           : self.pid,
            "status"        : self.status,
            "return_code"   : self.return_code,
            "signal_name"   : self.signal_name,
            "rusage"        : self.rusage,
        }



def wait(running: Running, prog_dir) -> Result:
    # Block until the process terminates.
    prog_dir.log(f"waiting for pid {running.pid}")
    pid, status, rusage = os.wait4(running.pid, 0)
    prog_dir.log(f"process terminated with status {status}")
    assert pid == running.pid
    return Result(running, status, rusage)


def run(prog, prog_dir) -> Result:
    return wait(start(prog, prog_dir), prog_dir)


#-------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", metavar="PROG.JSON",
        help="specification of program to run")
    parser.add_argument(
        "--background", default=False, action="store_true",
        help="go into background and after starting program")
    parser.add_argument(
        "--callback", metavar="URL",
        help="callback URL")
    parser.add_argument(
        "--print", default=False, action="store_true",
        help="print messages to stdout")
    parser.add_argument(
        "--no-clean", dest="clean", default=True, action="store_false",
        help="don't clean up program directory")
    args = parser.parse_args()

    with open(args.path, "r") as file:
        prog = json.load(file)

    prog_dir = ProgDir(prog)
    try:
        running = start(prog, prog_dir)
        if args.print:
            jso = running.to_jso()
            jso["prog_dir"] = prog_dir.to_jso()
            print(json.dumps(jso, indent=2))

        result = wait(running, prog_dir)
        if args.print:
            jso = result.to_jso()
            jso["prog_dir"] = prog_dir.to_jso()
            print(json.dumps(jso, indent=2))

    finally:
        if args.clean:
            prog_dir.clean()


if __name__ == "__main__":
    main()

