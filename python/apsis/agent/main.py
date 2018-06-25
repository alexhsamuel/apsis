import argparse
from   contextlib import suppress
import getpass
import logging
import os
from   pathlib import Path
import sanic
import sanic.response
import signal
import sys
import tempfile
import time

from   .api import API
from   .processes import Processes

#-------------------------------------------------------------------------------

DEFAULT_PORT = 5001

# FIXME: Deduplicate with apsis.service.main.

LOG_FORMATTER = logging.Formatter(
    fmt="%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
    datefmt="%H:%M:%S",
)
LOG_FORMATTER.converter = time.gmtime  # FIXME: Use ora.

SANIC_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "loggers": {
        "root": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_console"],
            "propagate": False,
            "qualname": "sanic.error",
        },

        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_console"],
            "propagate": False,
            "qualname": "sanic.access",
        }
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stderr,
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stderr,
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stderr,
        },
    },

    "formatters": {
        "generic": {
            "format": "%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
            "class": "logging.Formatter"
        },
        "access": {
            "format": "%(asctime)s %(name)-18s [%(levelname)-7s] [%(host)s %(request)s %(status)d %(byte)d] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
            "class": "logging.Formatter"
        },
    },

}
    
#-------------------------------------------------------------------------------

def get_state_dir():
    """
    Returns the state directory path, creating it if necessary.
    """
    user = getpass.getuser()
    path = Path(tempfile.gettempdir()) / f"apsis-agent-{user}"
    with suppress(FileExistsError):
        os.mkdir(path, mode=0o700)
    os.chmod(path, 0o700)
    return path


#-------------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
        datefmt="%H:%M:%S"
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--debug", action="store_true", default=False,
        help="run in debug mode")
    # FIXME: Can't use localhost on OSX, where it resolves to an IPV6 address,
    # until we pick up this Sanic fix:
    # https://github.com/channelcat/sanic/pull/1053
    parser.add_argument(
        "--host", metavar="HOST", default="127.0.0.1",
        help="server host address")
    parser.add_argument(
        "--port", metavar="PORT", type=int, default=DEFAULT_PORT,
        help="server port")
    parser.add_argument(
        "--no-daemon", action="store_true", default=False,
        help="don't daemonize; run in foreground")
    parser.add_argument(
        "--no-shutdown", action="store_true", default=False,
        help="don't shut down automatically after last process")
    args = parser.parse_args()
    daemon = not args.no_daemon

    state_dir = get_state_dir()
    logging.info(f"using dir: {state_dir}")

    app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
    app.config.LOGO = None

    app.config.auto_shutdown = not args.no_shutdown
    app.processes = Processes(state_dir)
    signal.signal(signal.SIGCHLD, app.processes.sigchld)

    app.blueprint(API, url_prefix="/api/v1")

    if daemon:
        # Redirect stdin from /dev/null.
        null_fd = os.open("/dev/null", os.O_RDONLY)
        os.dup2(null_fd, 0)
        os.close(null_fd)

        # Redirect stdout/stderr to a log file.
        log_path = state_dir / "log"
        logging.info(f"redirecting logs: {log_path}")
        log_fd = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY)
        os.dup2(log_fd, 1)
        os.dup2(log_fd, 2)
        os.close(log_fd)

    # FIXME: auto_reload added to sanic after 0.7.
    app.run(
        host    =args.host,
        port    =args.port,
        debug   =args.debug,
    )
    # FIXME: Kill and clean up procs on shutdown.


if __name__ == "__main__":
    main()

