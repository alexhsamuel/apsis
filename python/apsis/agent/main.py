import argparse
import logging
import os
from   pathlib import Path
import sanic
import sanic.response
import signal
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
    **sanic.log.LOGGING_CONFIG_DEFAULTS,
    "formatters": {
        "generic": {
            "class": "logging.Formatter",
            "format": "%(asctime)s %(name)-18s [%(levelname)-7s] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
        },
        "access": {
            "class": "logging.Formatter",
            "format": "%(asctime)s %(name)-18s [%(levelname)-7s] [%(host)s %(request)s %(status)d %(byte)d] %(message)s",
            "datefmt": LOG_FORMATTER.datefmt,
        },
    }
}    
    
#-------------------------------------------------------------------------------

app = sanic.Sanic(__name__, log_config=SANIC_LOG_CONFIG)
app.config.LOGO = None

app.blueprint(API, url_prefix="/api/v1")

def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().handlers[0].formatter = LOG_FORMATTER

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
        "--no-shutdown", action="store_true", default=False,
        help="don't shut down automatically after last process")
    parser.add_argument(
        "dir", metavar="DIR", type=Path,
        help="state directory")
    args = parser.parse_args()

    if args.dir.exists():
        parser.error(f"state directory {args.dir} exists")
    os.mkdir(args.dir, mode=0o700)

    app.config.auto_shutdown = not args.no_shutdown

    app.processes = Processes(args.dir)
    signal.signal(signal.SIGCHLD, app.processes.sigchld)

    # FIXME: auto_reload added to sanic after 0.7.
    app.run(
        host    =args.host,
        port    =args.port,
        debug   =args.debug,
    )
    # FIXME: Kill and clean up procs on shutdown.


if __name__ == "__main__":
    main()

