"""
Tests conditions.
"""

from   contextlib import closing
from   pathlib import Path
import pytest
import time

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def inst():
    job_dir = Path(__file__).absolute().parent / "test_conditions_jobs"
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


@pytest.fixture
def client(inst, scope="module"):
    return inst.client


def test_args(client):
    """
    Tests that args in dependencies are processed correctly.
    """
    res = client.schedule("dependent", {"date": "2022-11-01", "color": "red"})
    run_id = res["run_id"]

    # This job depends on dependency(date=2022-11-01 flavor=vanilla) and
    # dependency(date=2022-11-01 flavor=chocolate).
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # Run the first of the dependencies.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "vanilla"})
    time.sleep(1)

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # This is not a dependency, as the date is wrong.
    res = client.schedule("dependency", {"date": "2022-12-25", "flavor": "chocolate"})
    time.sleep(1)

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # This is just the first dependency, run again.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "vanilla"})
    time.sleep(1)

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # Now run the second dependency.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "chocolate"})
    time.sleep(1)

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "running"


def test_skip_duplicate(client):
    """
    Tests that a run is skipped if an identical run is running.
    """
    # Start a run, which runs for 1 s.
    res = client.schedule("skippable", {"date": "2022-11-01"})
    run_id = res["run_id"]

    res = client.get_run(run_id)
    assert res["state"] == "running"

    # Start a couple of duplicates.
    res = client.schedule("skippable", {"date": "2022-11-01"})
    run_id0 = res["run_id"]
    res = client.schedule("skippable", {"date": "2022-11-01"})
    run_id1 = res["run_id"]

    # They both should have been skipped.
    res = client.get_run(run_id0)
    assert res["state"] == "skipped"
    res = client.get_run(run_id1)
    assert res["state"] == "skipped"

    # Start a job with a different date.
    res = client.schedule("skippable", {"date": "2022-12-25"})
    run_id2 = res["run_id"]

    # This should not have been skipped; its date is different.
    res = client.get_run(run_id2)
    assert res["state"] == "running"

    # Wait for the original run to complete.
    time.sleep(1)
    res = client.get_run(run_id)
    assert res["state"] == "success"

    # Now a rerun should be fine.
    res = client.schedule("skippable", {"date": "2022-11-01"})
    run_id3 = res["run_id"]

    res = client.get_run(run_id3)
    assert res["state"] == "running"


