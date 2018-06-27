import logging
import os

log = logging.getLogger("daemon")

#-------------------------------------------------------------------------------

def daemonize(log_path):
    # Redirect stdin from /dev/null.
    null_fd = os.open("/dev/null", os.O_RDONLY)
    os.dup2(null_fd, 0)
    os.close(null_fd)

    # Redirect stdout/stderr to a log file.
    logging.info(f"redirecting logs: {log_path}")
    log_fd = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(log_fd)

    # Double-fork to detach.
    log.info("detaching")
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)


