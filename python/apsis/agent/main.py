import argparse
from   contextlib import suppress
import getpass
import logging
import os
from   pathlib import Path
import sanic
import sanic.response
import signal
import socket
import sys
import tempfile
import time

from   . import DEFAULT_PORT
from   ..lib.daemon import daemonize
from   ..lib.pidfile import PidFile, PidExistsError
from   .api import API
from   .processes import Processes

#-------------------------------------------------------------------------------

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
        "--host", metavar="HOST", default="0.0.0.0",
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

    state_dir = get_state_dir()
    logging.debug(f"using dir: {state_dir}")

    app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
    app.config.LOGO = None
    app.config.auto_shutdown = not args.no_shutdown
    app.blueprint(API, url_prefix="/api/v1")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    logging.info(f"binding {args.port}")
    sock.bind((args.host, args.port))

    try:
        with PidFile(state_dir / "pid") as pid_file:
            app.processes = Processes(state_dir)
            signal.signal(signal.SIGCHLD, app.processes.sigchld)

            if not args.no_daemon:
                daemonize(state_dir / "log")

            pid_file.write()

            # FIXME: auto_reload added to sanic after 0.7.
            logging.info("running app")
            app.run(
                sock    =sock,
                debug   =args.debug,
            )
            # FIXME: Kill and clean up procs on shutdown.

    except PidExistsError as exc:
        if args.no_daemon:
            logging.critical(exc)
            raise SystemExit(2)


if __name__ == "__main__":
    main()

