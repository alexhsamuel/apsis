from   contextlib import contextmanager
import os
from   pathlib import Path
import pytest

from   honcho import fork_exec

#-------------------------------------------------------------------------------

@contextmanager
def null():
    with open("/dev/null", "w") as file:
        yield file.fileno()
    

#-------------------------------------------------------------------------------

def test_no_program():
    with pytest.raises(FileNotFoundError), null() as nfd:
        fork_exec(["/bin/bogusbogus"], "/", None, nfd, nfd, nfd)


def test_not_executable():
    with pytest.raises(PermissionError), null() as nfd:
        fork_exec(["/etc/hosts"], "/", None, nfd, nfd, nfd)


def test_cwd_root(tmpdir):
    cwd_path = Path(tmpdir) / "cwd.txt"
    with open(cwd_path, "w+") as file, null() as nfd:
        pid = fork_exec(["/bin/pwd"], "/", {}, nfd, file.fileno(), nfd)
        os.wait4(pid, 0)
        file.seek(0)
        proc_cwd = file.read()

    assert proc_cwd.strip() == "/"


def test_cwd_current(tmpdir):
    cwd_path = Path(tmpdir) / "cwd.txt"
    with open(cwd_path, "w+") as file, null() as nfd:
        pid = fork_exec(["/bin/pwd"], tmpdir, {}, nfd, file.fileno(), nfd)
        os.wait4(pid, 0)
        file.seek(0)
        proc_cwd = file.read()

    assert proc_cwd.strip() == tmpdir


def test_env_empty(tmpdir):
    env_path = Path(tmpdir) / "env.txt"
    with open(env_path, "w+") as file, null() as nfd:
        pid = fork_exec(["/usr/bin/env"], "/", {}, nfd, file.fileno(), nfd)
        os.wait4(pid, 0)
        file.seek(0)
        proc_env = file.read()

    proc_env = dict( e.split("=", 1) for e in proc_env.splitlines() )
    assert len(proc_env) == 0


def test_env_simple(tmpdir):
    env_path = Path(tmpdir) / "env.txt"
    env = {"foo": "bar", "value": 42, "LONG_NAME": "The quick brown fox."}
    with open(env_path, "w+") as file, null() as nfd:
        pid = fork_exec(["/usr/bin/env"], "/", env, nfd, file.fileno(), nfd)
        os.wait4(pid, 0)
        file.seek(0)
        proc_env = file.read()

    proc_env = dict( e.split("=", 1) for e in proc_env.splitlines() )
    assert len(proc_env) == 3
    assert proc_env["foo"] == "bar"
    assert proc_env["value"] == "42"
    assert proc_env["LONG_NAME"] == "The quick brown fox."


