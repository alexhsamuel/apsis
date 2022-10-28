"""
Tests basic transitions by running an Apsis service and interacting with it
via the HTTP client.
"""

from   contextlib import closing
import ora
import pytest

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def inst():
    with closing(ApsisInstance()) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


def test_create_adhoc(inst):
    client = inst.client

    # Create and schedule a run.
    res = client.schedule_adhoc("now", {"program": {"type": "no-op"}})
    job_id = res["job_id"]
    run_id = res["run_id"]

    # Check on the adhoc job.
    job = client.get_job(job_id)
    assert job["program"]["type"] == "no-op"

    # Check on the run.
    run = client.get_run(run_id)
    assert run["job_id"] == job_id
    # It should be done.
    assert run["state"] == "success"


def test_skip(inst):
    """
    Schedules a new run for the future and skips it before it runs.
    """
    client = inst.client

    # Create and schedule a run for a minute from now.
    res = client.schedule_adhoc(ora.now() + 60, {"program": {"type": "no-op"}})
    run_id = res["run_id"]

    # It should be scheduled.
    run = client.get_run(run_id)
    assert run["state"] == "scheduled"

    # Skip the run.
    client.skip(run_id)

    # It should be skipped.
    run = client.get_run(run_id)
    assert run["state"] == "skipped"


