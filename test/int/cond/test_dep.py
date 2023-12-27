"""
Tests dependency conditions.
"""

from   contextlib import closing
from   pathlib import Path
import pytest
import random
import time

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

job_dir = Path(__file__).absolute().parent / "jobs"

@pytest.fixture(scope="function")
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


@pytest.mark.parametrize("direction", ["forward", "backward", "shuffle"])
def test_many_deps(inst, direction):
    """
    Tests a job with a large number of conditions.

    :param direction:
      Order in which the dependencies are run, relative to specified.
    """
    client = inst.client

    # Create a job with many dependencies.
    vals = [ format(i, "03d") for i in range(200) ]
    job = {
        "program": {"type": "no-op"},
        "condition": [
            {
                "type": "dependency",
                "job_id": "many dep",
                "args": {"val": v},
            }
            for v in vals
        ]
    }

    res = client.schedule_adhoc("now", job)
    run_id = res["run_id"]
    assert res["state"] == "waiting"

    # Run the dependencies, in order depending on `direction`.
    match direction:
        case "forward":
            pass
        case "backward":
            vals = vals[:: -1]
        case "shuffle":
            random.shuffle(vals)
        case _:
            assert False

    # All dependencies but one.
    for v in vals[: -1]:
        client.schedule("many dep", {"val": v})

    time.sleep(1)
    # The run is still waiting.
    res = client.get_run(run_id)
    assert res["state"] == "waiting"

    # Schedule the last dependency.
    client.schedule("many dep", {"val": vals[-1]})

    # Now the run can continue.s
    res = inst.wait_run(run_id)
    assert res["state"] == "success"


