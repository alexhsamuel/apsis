from   pathlib import Path
import time

from   procstar_instance import ApsisService
from   apsis.jobs import jso_to_job, dump_job

#-------------------------------------------------------------------------------

IGNORE_TERM_PATH = Path(__file__).parent / "ignore-term"

JOB_ID = "ignore term"
JOB = jso_to_job({
    "params": ["time"],
    "program": {
        "type": "procstar",
        "argv": [IGNORE_TERM_PATH, "{{ time }}"],
        "stop": {
            "grace_period": 2,
        },
    }
}, JOB_ID)

def test_dont_stop():
    svc = ApsisService()
    dump_job(svc.jobs_dir, JOB)
    with svc, svc.agent():
        # Schedule a 1 sec run but tell Apsis to stop it after 3 sec.
        run_id = svc.client.schedule(JOB_ID, {"time": "1"}, stop_time="+3s")["run_id"]
        res = svc.wait_run(run_id)

        assert res["state"] == "success"
        meta = res["meta"]["program"]
        assert meta["status"]["exit_code"] == 0
        assert meta["stop"]["signals"] == []
        assert meta["times"]["elapsed"] < 2


def test_kill():
    svc = ApsisService()
    dump_job(svc.jobs_dir, JOB)
    with svc, svc.agent():
        # Schedule a 5 sec run but tell Apsis to stop it after 1 sec.  The
        # process ignores SIGTERM so Apsis will send SIGQUIT after the grace
        # period.
        run_id = svc.client.schedule(JOB_ID, {"time": "5"}, stop_time="+1s")["run_id"]

        time.sleep(1.5)
        res = svc.client.get_run(run_id)
        assert res["state"] == "stopping"
        meta = res["meta"]["program"]

        res = svc.wait_run(run_id)

        assert res["state"] == "failure"
        meta = res["meta"]["program"]
        assert meta["status"]["signal"] == "SIGKILL"
        assert meta["stop"]["signals"] == ["SIGTERM", "SIGKILL"]
        assert meta["times"]["elapsed"] > 2.8


