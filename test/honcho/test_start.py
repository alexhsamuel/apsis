import pytest

from   honcho import start

#-------------------------------------------------------------------------------

def test_no_program():
    with pytest.raises(FileNotFoundError), \
         open("/dev/null", "w") as file:
        fd = file.fileno()
        start(["/bin/bogusbogus"], "/", None, fd, fd, fd)


def test_not_executable():
    with pytest.raises(PermissionError), \
         open("/dev/null", "w") as file:
        fd = file.fileno()
        start(["/etc/hosts"], "/", None, fd, fd, fd)
    

