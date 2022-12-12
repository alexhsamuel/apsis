from   contextlib import closing
import time

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

def test_waiting_max_time():
    CFG = {
        "waiting": {
            "max_time": 1.5,
        }
    }
    with closing(ApsisInstance(cfg=CFG)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()

        client = inst.client

        res = client.schedule_adhoc("now", {
            "program": "no-op",
            "condition": {
                "type": "const",
                "value": False,
            },
        })
        run_id = res["run_id"]

        run = client.get_run(run_id)
        assert run["state"] == "waiting"

        time.sleep(1.5)

        run = client.get_run(run_id)
        assert run["state"] == "error"
        run_log = client.get_run_log(run_id)
        assert "time out" in run_log[-1]["message"]


