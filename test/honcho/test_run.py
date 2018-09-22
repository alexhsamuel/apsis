from   honcho import run

#-------------------------------------------------------------------------------

def test_argv_echo():
    prog = {
        "argv": ["/bin/echo", "Hello,", "world!", "This is a test."],
    }

    with run(prog) as result:
        assert result.status == 0
        assert result.return_code == 0
        assert result.signal_name is None
        assert result.get_stdout() == b"Hello, world! This is a test.\n"
        prog_dir_path = result.prog_dir.path

    assert not prog_dir_path.exists()


def test_cmd_echo():
    prog = {
        "cmd": "echo 'Hello, world!'; echo This is a test.",
    }

    with run(prog) as result:
        assert result.status == 0
        assert result.return_code == 0
        assert result.signal_name is None
        assert result.get_stdout() == b"Hello, world!\nThis is a test.\n"


