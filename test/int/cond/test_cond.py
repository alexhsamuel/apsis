"""
Tests conditions.
"""

from   contextlib import closing
from   pathlib import Path
import pytest
import time

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

job_dir = Path(__file__).absolute().parent / "jobs"

@pytest.fixture(scope="module")
def inst():
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


@pytest.fixture
def client(inst, scope="function"):
    return inst.client


def test_args_match(inst):
    """
    Tests that args in dependencies are processed correctly.
    """
    client = inst.client

    res = client.schedule("dependent", {"date": "2022-11-01", "color": "red"})
    run_id = res["run_id"]

    # This job depends on dependency(date=2022-11-01 flavor=vanilla) and
    # dependency(date=2022-11-01 flavor=chocolate).
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # Run the first of the dependencies.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "vanilla"})

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # This is not a dependency, as the date is wrong.
    res = client.schedule("dependency", {"date": "2022-12-25", "flavor": "chocolate"})

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # This is just the first dependency, run again.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "vanilla"})

    # One dependency satisfied, but not the other one.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # Now run the second dependency.
    res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "chocolate"})
    inst.wait_run(res["run_id"])

    # Both are satisfied.
    res = inst.wait_run(run_id)
    assert res["state"] == "success"


def test_args_max_waiting():
    """
    Tests that a run waiting for more than `waiting.max_time` is
    transitioned to error.
    """
    with closing(ApsisInstance(job_dir=job_dir, port=5006)) as inst:
        inst.create_db()
        inst.write_cfg({"waiting": {"max_time": 1}})
        inst.start_serve()
        inst.wait_for_serve()
        client = inst.client

        res = client.schedule("dependent", {"date": "2022-11-01", "color": "red"})
        run_id = res["run_id"]

        # This job depends on dependency(date=2022-11-01 flavor=vanilla) and
        # dependency(date=2022-11-01 flavor=chocolate).
        res = client.get_run(run_id)
        assert res["state"] == "waiting"

        # Run the first of the dependencies.
        res = client.schedule("dependency", {"date": "2022-11-01", "flavor": "vanilla"})
        time.sleep(1.1)

        # After a second, its second dependency is not yet satisified, so it is
        # transitioned to error.
        res = client.get_run(run_id)
        assert res["state"] == "error"


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


def test_to_error(client):
    """
    Tests a custom skip_duplicate condition, which transitions runs to error if
    there is already a failure or error run.
    """
    res = client.schedule("to error", {"color": "red"})
    red0 = res["run_id"]
    res = client.schedule("to error", {"color": "red"})
    red1 = res["run_id"]
    res = client.schedule("to error", {"color": "blue"})
    blue0 = res["run_id"]

    # All should run immediately.
    for run_id in (red0, red1, blue0):
        res = client.get_run(run_id)
        assert res["state"] == "running"

    # All should succeed.
    time.sleep(1)
    for run_id in (red0, red1, blue0):
        res = client.get_run(run_id)
        assert res["state"] == "success"

    # Now mark a red one as failed.
    res = client.mark(red1, "failure")

    # Schedule another red and blue run.
    res = client.schedule("to error", {"color": "red"})
    red2 = res["run_id"]
    res = client.schedule("to error", {"color": "blue"})
    blue1 = res["run_id"]

    # The red one should have been transitioned to error.
    res = client.get_run(red2)
    assert res["state"] == "error"
    res = client.get_run(blue1)
    assert res["state"] == "running"

    # Mark both failure/error runs as success.
    res = client.mark(red1, "success")
    res = client.mark(red2, "success")

    # A red run should go again.
    res = client.schedule("to error", {"color": "red"})
    red3 = res["run_id"]
    res = client.get_run(red3)
    assert res["state"] == "running"



