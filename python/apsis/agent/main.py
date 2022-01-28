import argparse
from   contextlib import suppress
import errno
import logging
import os
from   pathlib import Path
import pwd
import sanic
import sanic.response
import secrets
import signal
import socket
import ssl
import sys
import tempfile
import time

from   . import DEFAULT_PORT, SSL_CERT, SSL_KEY
from   ..lib.daemon import daemonize
from   ..lib.pidfile import PidFile
from   .api import API
from   .processes import Processes

#-------------------------------------------------------------------------------

# FIXME: Deduplicate with apsis.service.main.

LOG_FORMATTER = logging.Formatter(
    fmt="%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
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
        "sanic": {
            "level": "INFO",
            "propagate": True,
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
    user = pwd.getpwuid(os.getuid()).pw_name
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
        "--log-level", metavar="LEVEL", default=None,
        choices={"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"},
        help="log at LEVEL [def: INFO]")
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
    parser.add_argument(
        "--stop-time", metavar="SECS", default=300,
        help="wait SECS after last process before stopping [def: 300]")
    args = parser.parse_args()

    if args.log_level is not None:
        logging.getLogger(None).setLevel(getattr(logging, args.log_level))

    state_dir = get_state_dir()
    print(f"using dir: {state_dir}", file=sys.stderr)

    # Check the pid file.  Is there already an instance running?
    pid_file = PidFile(state_dir / "pid")
    pid = pid_file.lock()

    if pid is None:
        # Our pid file, so no agent currently running.

        if args.connect:
            print("agent not running", file=sys.stderr)
            raise SystemExit(1)

        print("starting new agent", file=sys.stderr)
        uid = pwd.getpwuid(os.getuid())
        euid = pwd.getpwuid(os.geteuid())
        print(
            f"uid={uid.pw_uid}/{uid.pw_name} euid={euid.pw_uid}/{euid.pw_name}",
            file=sys.stderr)

        port, sock = make_server_socket(
            args.bind, range(DEFAULT_PORT, DEFAULT_PORT + 100))
        token = secrets.token_urlsafe()
        pid_data = encode_pid_data(port, token)

        # Print the port and token for the client to grab.
        print(pid_data)
        sys.stdout.flush()

        # Write the port and token to the pid file, for other clients.
        pid_file.file.write(pid_data)
        pid_file.file.flush()

        # Start the agent.
        if args.log_level is not None:
            for section in SANIC_LOG_CONFIG["loggers"].values():
                section["level"] = args.log_level
        app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
        app.config.LOGO = None
        app.config.auto_stop = None if args.no_stop else args.stop_time
        app.blueprint(API, url_prefix="/api/v1")
        app.token = token

        app.processes = Processes(state_dir)
        signal.signal(signal.SIGCHLD, app.processes.sigchld)

        # SSL certificates are stored in this directory.
        ssl_context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(SSL_CERT, keyfile=SSL_KEY)

        if not args.no_daemon:
            daemonize(state_dir / "log")

        logging.info(f"pid={os.getpid()}")
        uid = pwd.getpwuid(os.getuid())
        euid = pwd.getpwuid(os.geteuid())
        logging.info(f"uid={uid.pw_uid}/{uid.pw_name} euid={euid.pw_uid}/{euid.pw_name}")

        # FIXME: auto_reload added to sanic after 0.7.
        logging.info("running app")
        app.run(
            sock    =sock,
            ssl     =ssl_context,
            # FIXME: Debug seems to be completely broken?
            # debug   =args.debug,
        )

    else:
        # Found a running agent.

        pid_data = pid_file.file.read()
        port, token = decode_pid_data(pid_data)
        print(f"existing agent: port={port}", file=sys.stderr)

        if args.no_connect:
            print(
                f"agent already running; port {port}",
                file=sys.stderr)
            raise SystemExit(1)

        # Print the pid and token for the client to grab.
        print(pid_data)

    pid_file.unlock()


if __name__ == "__main__":
    main()
