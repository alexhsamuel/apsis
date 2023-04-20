import logging
from   pathlib import Path
import yaml

from   .actions import Action
from   .lib.imp import import_fqname
from   .lib.json import to_array
from   .lib.py import nfloat
from   .program import Program
from   .schedule import Schedule

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

def normalize_path(path, base_path: Path):
    path = Path(path)
    if not path.is_absolute():
        path = base_path / path
    return path


def check(cfg, base_path: Path):
    job_dir = normalize_path(cfg.get("job_dir", "jobs"), base_path)
    if not job_dir.exists():
        log.error(f"missing job directory: {job_dir}")
    cfg["job_dir"] = job_dir

    database = normalize_path(cfg.get("database", "apsis.db"), base_path)
    if not database.exists():
        log.error(f"missing database: {database}")
    cfg["database"] = database

    cfg["actions"] = to_array(cfg.get("action", []))

    waiting = cfg["waiting"] = cfg.setdefault("waiting", {})
    max_time = waiting["max_time"] = nfloat(waiting.get("max_time", None))
    if max_time is not None and max_time <= 0:
        log.error("negative waiting.max_time: {max_time}")

    # runs_lookback → runs.lookback
    try:
        lookback = cfg["runs_lookback"]
    except KeyError:
        pass
    else:
        warnings.warn("config runs_lookback → runs.lookback", DeprecationWarning)
        cfg.setdefault("runs", {}).setdefault("lookback", lookback)

    return cfg


def load(path):
    """
    Loads configuration from `path`.

    If path is none, uses default configuration, based in the CWD.
    """
    if path is None:
        return check({}, Path.cwd())
    else:
        path = Path(path)
        with open(path) as file:
            cfg = yaml.load(file, Loader=yaml.BaseLoader)
            if cfg is None:
                # Empty config.
                cfg = {}
        return check(cfg, path.parent.absolute())


