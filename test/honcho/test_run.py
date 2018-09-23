from   honcho import run, ProgDir

#-------------------------------------------------------------------------------

def test_argv_echo():
    prog = {
        "argv": ["/bin/echo", "Hello,", "world!", "This is a test."],
    }

    prog_dir = ProgDir(prog)
    with prog_dir:
        result = run(prog, prog_dir)
        assert result.status == 0
        assert result.return_code == 0
        assert result.signal_name is None
        assert prog_dir.get_stdout() == b"Hello, world! This is a test.\n"

    assert prog_dir.path is None


def test_cmd_echo():
    prog = {
        "cmd": "echo 'Hello, world!'; echo This is a test.",
    }

    with ProgDir(prog) as prog_dir:
        result = run(prog, prog_dir)
        assert result.status == 0
        assert result.return_code == 0
        assert result.signal_name is None
        assert prog_dir.get_stdout() == b"Hello, world!\nThis is a test.\n"


