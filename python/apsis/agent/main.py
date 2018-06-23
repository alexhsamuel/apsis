import argparse
import logging
import os
from   pathlib import Path
import sanic
import sanic.response
import time

from   .api import API

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
    parser.add_argument(
        "--host", metavar="HOST", default="localhost",
        help="server host address")
    parser.add_argument(
        "--port", metavar="PORT", type=int, default=DEFAULT_PORT,
        help="server port")
    parser.add_argument(
        "dir", metavar="DIR", type=Path,
        help="state directory")
    args = parser.parse_args()

    if args.dir.exists():
        parser.error(f"state directory {args.dir} exists")
    os.mkdir(args.dir, mode=0o700)
    
    # FIXME: auto_reload added to sanic after 0.7.
    app.run(
        host    =args.host,
        port    =args.port,
        debug   =args.debug,
    )


if __name__ == "__main__":
    main()

