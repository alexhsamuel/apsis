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


def test_timeout(inst):
    """
    Tests agent program timeout.
    """
    import logging
    logging.warning("this is logging")

    client = inst.client
    # The program runs for 3 s, so these three runs will time out.
    r0 = client.schedule("timeout", {"timeout": 0})["run_id"]
    r1 = client.schedule("timeout", {"timeout": 1})["run_id"]
    r2 = client.schedule("timeout", {"timeout": 2})["run_id"]
    # These two runs will succeed.
    r4 = client.schedule("timeout", {"timeout": 4})["run_id"]
    r5 = client.schedule("timeout", {"timeout": 5})["run_id"]

    time.sleep(2)
    res = client.get_run(r0)
    assert res["state"] == "failure"
    res = client.get_run(r2)
    assert res["state"] == "running"

    time.sleep(2)
    res = client.get_run(r1)
    assert res["state"] == "failure"
    res = client.get_run(r2)
    assert res["state"] == "failure"
    res = client.get_run(r4)
    assert res["state"] == "success"
    res = client.get_run(r5)
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

    time.sleep(2)
    res = client.get_run(r0)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGTERM"
    res = client.get_run(r1)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGKILL"
    res = client.get_run(r2)
    assert res["state"] == "failure"
    assert res["meta"]["signal"] == "SIGUSR2"

