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


def wait_run(client, run_id):
    """
    Polls for a run to no longer be running.
    """
    while True:
        res = client.get_run(run_id)
        if res["state"] in ("starting", "running"):
            time.sleep(0.1)
            continue
        else:
            return res


def test_timeout(inst):
    """
    Tests agent program timeout.
    """
    client = inst.client
    # The program runs for 3 s, so these three runs will time out.
    r0 = client.schedule("timeout", {"timeout": 0})["run_id"]
    r1 = client.schedule("timeout", {"timeout": 1})["run_id"]
    r2 = client.schedule("timeout", {"timeout": 2})["run_id"]
    # These two runs will succeed.
    r4 = client.schedule("timeout", {"timeout": 4})["run_id"]
    r5 = client.schedule("timeout", {"timeout": 5})["run_id"]

    res = wait_run(client, r0)
    assert res["state"] == "failure"
    res = client.get_run(r2)
    assert res["state"] == "running"

    time.sleep(2)
    res = wait_run(client, r1)
    assert res["state"] == "failure"
    res = wait_run(client, r2)
    assert res["state"] == "failure"
    res = wait_run(client, r4)
    assert res["state"] == "success"
    res = wait_run(client, r5)
    assert res["state"] == "success"


def test_signal(inst):
    """
    Tests signal when agent program times out.
    """
    client = inst.client
    r0 = client.schedule("signal", {"signal": "TERM"})["run_id"]
    r1 = client.schedule("signal", {"signal": "SIGKILL"})["run_id"]
    r2 = client.schedule("signal", {"signal": 12})["run_id"]  # SIGUSR2

    assert client.get_run(r0)["state"] == "running"
    assert client.get_run(r1)["state"] == "running"
    assert client.get_run(r2)["state"] == "running"

    res = wait_run(client, r0)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGTERM"
    res = wait_run(client, r1)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGKILL"
    res = wait_run(client, r2)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGUSR2"


