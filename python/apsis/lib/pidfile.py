import logging
import os
from   pathlib import Path

log = logging.getLogger("pidfile")

#-------------------------------------------------------------------------------

class PidExistsError(RuntimeError):
    """
    The pid file indicates a running process.
    """

    def __init__(self, pid, data):
        super().__init__(f"process already running: {pid}")
        self.pid = pid
        self.data = data



class PidFile:
    """
    Pid file context manager.
    """

    def __init__(self, path):
        self.path = Path(path)


    def get_pid(self):
        """
        Checks if the process is running.

        :return:
          The pid and associated data of the running process, if any, or 
          `None, None` otherwise.
        """
        # Try to read a pid from the pid file.
        try:
            with open(self.path, "rt") as file:
                pid = int(next(file).strip())
                data = file.read()
        except Exception as exc:
            log.debug(f"can't read pidfile: {self.path}: {exc}")
            return None, None
        # Check if the process exists.
        try:
            os.kill(pid, 0)
        except PermissionError:
            # Not our process, but that's OK.
            return pid, data
        except ProcessLookupError:
            # No such process.  
            self.remove()
            return None, None
        else:
            return pid, data


    def write(self, pid=None, data=""):
        """
        Writes the pid file.
        """
        if pid is None:
            pid = os.getpid()
        contents = (str(pid) + "\n" + data).encode()

        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        else:
            os.write(fd, contents)
            os.close(fd)


    def remove(self):
        """
        Removes the pid file.
        """
        try:
            os.unlink(self.path)
        except Exception as exc:
            log.debug(f"failed to remove pid file: {self.path}: {exc}")


    def __enter__(self):
        """
        Does not write the pid file.
        """
        pid, data = self.get_pid()
        if pid is None:
            pass
        else:
            raise PidExistsError(pid, data)
        return self


    def __exit__(self, exc_type, exc, exc_tb):
        self.remove()



