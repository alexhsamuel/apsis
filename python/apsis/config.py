import logging
from   pathlib import Path
import yaml

from   .lib.json import to_array

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
        return check(cfg, path.parent.absolute())


