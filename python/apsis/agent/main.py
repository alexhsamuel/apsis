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
from   ..lib.pidfile import PidFile
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

def make_server_socket(host, ports):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    for port in range(DEFAULT_PORT, DEFAULT_PORT + 100):
        try:
            sock.bind((host, port))
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                continue
            else:
                raise
        else:
            return port, sock
    else:
        print("can't bind", file=sys.stderr)
        raise SystemExit(1)


def encode_pid_data(port, token):
    return f"{port} {token}"


def decode_pid_data(pid_data):
    port, token = pid_data.split()
    return int(port), token


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
    excl = parser.add_mutually_exclusive_group()
    excl.add_argument(
        "--no-connect", action="store_true", default=False,
        help="start only; fail if already running")
    excl.add_argument(
        "--connect", action="store_true", default=False,
        help="reconnect only; fail if not running")
    parser.add_argument(
        "--no-daemon", action="store_true", default=False,
        help="don't daemonize; run in foreground")
    parser.add_argument(
        "--no-stop", action="store_true", default=False,
        help="don't stop automatically after last process")
    args = parser.parse_args()

    state_dir = get_state_dir()
    logging.debug(f"using dir: {state_dir}")

    pid_file = PidFile(state_dir / "pid")
    pid, pid_data = pid_file.get_pid()

    if pid is None:
        # No agent runnong.
        if args.connect:
            print("agent not running", file=sys.stderr)
            raise SystemExit(1)

        # Start the agent.
        try:
            app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
            app.config.LOGO = None
            app.config.auto_stop = not args.no_stop
            app.blueprint(API, url_prefix="/api/v1")

            app.processes = Processes(state_dir)
            signal.signal(signal.SIGCHLD, app.processes.sigchld)

            port, sock = make_server_socket(
                args.bind, range(DEFAULT_PORT, DEFAULT_PORT + 100))

            token = secrets.token_urlsafe()

            pid_data = encode_pid_data(port, token)
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

        finally:
            pid_file.remove()

    else:
        # Found a running agent.
        port, token = decode_pid_data(pid_data)

        if args.no_connect:
            print(f"agent running; pid {pid} port {port}", file=sys.stderr)
            raise SystemExit(1)

        print(pid_data)


if __name__ == "__main__":
    main()

