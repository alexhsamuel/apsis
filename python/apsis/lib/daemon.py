import logging
import os

log = logging.getLogger("daemon")

#-------------------------------------------------------------------------------

def daemonize(log_path):
    pid = os.getpid()
    import subprocess
    subprocess.run(f"/usr/bin/ls -l /proc/{pid}/fd 1>&2", shell=True, check=True)

    # Redirect stdin from /dev/null.
    null_fd = os.open("/dev/null", os.O_RDONLY)
    os.dup2(null_fd, 0)
    os.close(null_fd)

    # Redirect stdout/stderr to a log file.
    logging.debug(f"redirecting logs: {log_path}")
    log_fd = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
    os.dup2(log_fd, 1)
    subprocess.run(f"/usr/bin/ls -l /proc/{pid}/fd 1>&2", shell=True, check=True)
    os.dup2(log_fd, 2)
    os.close(log_fd)

    os.closerange(10, get_max_fds())

    # Double-fork to detach.
    log.info(f"detaching {os.getpid()} {os.getppid()}")
    if os.fork() > 0:
        log.info(f"first exit {os.getpid()} {os.getppid()}")
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        log.info(f"second exit {os.getpid()} {os.getppid()}")
        os._exit(0)
    log.info(f"detached {os.getpid()} {os.getppid()}")


import resource
def get_max_fds():
    _, limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    return 2048 if limit == resource.RLIM_INFINITY else limit


