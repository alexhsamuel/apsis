from   pathlib import Path

from   instance import ApsisService

JOB_DIR = Path(__file__).parent / "jobs"

#-------------------------------------------------------------------------------

def test_rerun():
    with ApsisService(job_dir=JOB_DIR) as inst:
        run_id = inst.client.schedule(
            "print time", {"color": "green", "exit": "4"}
        )["run_id"]
        res = inst.wait_run(run_id)
        assert res["state"] == "failure"
        assert res["meta"]["program"]["return_code"] == 4
        output = inst.client.get_output(run_id, "output")

        run_id = inst.client.rerun(run_id)["run_id"]
        res = inst.wait_run(run_id)
        # print(res)
        # assert False
        # assert res["state"] == "failure"
        # assert res["meta"]["program"]["return_code"] == 4
        # new_output = inst.client.get_output(run_id, "output")
        # assert new_output.startswith("color=green")
        # assert new_output != output


