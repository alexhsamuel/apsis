from   pathlib import Path

from   procstar_instance import ApsisService

JOB_DIR = Path(__file__).parent / "jobs"

#-------------------------------------------------------------------------------

def test_program():
    with ApsisService(job_dir=JOB_DIR) as svc, svc.agent(serve=True) as agent:
        assert len(agent.client.get_procs()) == 0
        run_id = svc.client.schedule("sleep", {"time": 1})["run_id"]
        res = svc.wait_run(run_id, timeout=5)
        assert res["state"] == "success"
        assert len(agent.client.get_procs()) == 0


def test_reconnect():
    """
    Tests reconnecting to a running run after Apsis restart.
    """
    with ApsisService(job_dir=JOB_DIR) as svc, svc.agent(serve=True) as agent:
        run_id = svc.client.schedule("sleep", {"time": 1})["run_id"]
        # Wait for the run to start; we can't reconnect to starting runs.
        res = svc.wait_run(run_id, wait_states=("starting", ))
        assert res["state"] == "running"

        svc.restart()

        res = svc.wait_run(run_id, timeout=5)
        assert res["state"] == "success"
        assert len(agent.client.get_procs()) == 0


def test_reconnect_many(num=256):
    """
    Tests reconnecting to many running runs after Apsis restart.
    """
    with ApsisService(job_dir=JOB_DIR) as svc, svc.agent(serve=True) as agent:
        run_ids = [
            svc.client.schedule("sleep", {"time": 1})["run_id"]
            for _ in range(num)
        ]
        # Wait for the runs to start; we can't reconnect to starting runs.
        for run_id in run_ids:
            res = svc.wait_run(run_id, wait_states=("starting", ))
            # Some may have completed already.
            assert res["state"] in {"running", "success"}

        svc.restart()

        for run_id in run_ids:
            res = svc.wait_run(run_id, timeout=5)
            assert res["state"] == "success"

        assert len(agent.client.get_procs()) == 0


# FIXME:
# - signal tests
# - procstar connection timeout and reconnect (SIGHUP)

