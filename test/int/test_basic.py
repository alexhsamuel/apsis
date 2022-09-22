from   contextlib import closing
from   pathlib import Path
import pytest
import sqlite3
import yaml

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def inst():
    with closing(ApsisInstance()) as inst:
        yield inst


def test_create_db(inst):
    inst.create_db()
    assert inst.db_path.is_file()
    with sqlite3.connect(inst.db_path) as db:
        with closing(db.cursor()) as cursor:
            cursor.execute("SELECT * FROM runs")
            names = { d[0] for d in cursor.description }
            assert "run_id" in names
            assert len(list(cursor)) == 0


def test_cfg(inst):
    jobs_dir = Path(__file__).parent / "jobs_basic"
    inst.write_cfg({
        "job_dir": str(jobs_dir),
    })
    assert inst.cfg_path.is_file()
    with open(inst.cfg_path) as file:
        cfg = yaml.load(file, yaml.SafeLoader)
    print(cfg)


def test_start_serve(inst):
    inst.start_serve()
    inst.wait_for_serve()


def test_jobs(inst):
    ret, jobs = inst.run_apsis_json("jobs")
    assert ret == 0
    assert len(jobs) == 1

    job = jobs[0]
    assert job["job_id"] == "job1"


def test_stop_serve(inst):
    ret = inst.stop_serve()
    assert ret == 0


