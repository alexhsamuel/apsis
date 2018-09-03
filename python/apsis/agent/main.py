import argparse
from   contextlib import suppress
import errno
import getpass
import logging
import os
from   pathlib import Path
import sanic
import sanic.response
import secrets
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
    parser.add_argument(
        "--bind", metavar="ADDR", default="0.0.0.0",
        help="bind server to interface ADDR [def: all]")
    parser.add_argument(
        "--no-daemon", action="store_true", default=False,
        help="don't daemonize; run in foreground")
    parser.add_argument(
        "--no-stop", action="store_true", default=False,
        help="don't stop automatically after last process")
    args = parser.parse_args()

    state_dir = get_state_dir()
    logging.debug(f"using dir: {state_dir}")

    app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
    app.config.LOGO = None
    app.config.auto_stop = not args.no_stop
    app.blueprint(API, url_prefix="/api/v1")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    try:
        with PidFile(state_dir / "pid") as pid_file:
            app.processes = Processes(state_dir)
            signal.signal(signal.SIGCHLD, app.processes.sigchld)

            for port in range(DEFAULT_PORT, DEFAULT_PORT + 100):
                try:
                    sock.bind((args.host, port))
                except OSError as exc:
                    if exc.errno == errno.EADDRINUSE:
                        continue
                    else:
                        raise
                break
            else:
                logging.critical(f"can't bind")
                raise SystemExit(1)

            token = secrets.token_urlsafe()

            pid_data = f"{port} {token}"
            print(pid_data)
            sys.stdout.flush()

            if not args.no_daemon:
                daemonize(state_dir / "log")

            pid_file.write(data=pid_data)

            # FIXME: auto_reload added to sanic after 0.7.
            logging.info("running app")
            app.run(
                sock    =sock,
                debug   =args.debug,
            )
            # FIXME: Kill and clean up procs on stop.

    except PidExistsError as exc:
        if args.no_daemon:
            logging.critical(exc)
            raise SystemExit(2)
        else:
            print(exc.data)


if __name__ == "__main__":
    main()

