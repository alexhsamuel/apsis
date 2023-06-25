from   contextlib import closing
import json
import ora
import time

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

def test_stats(tmp_path):
    path = tmp_path / "stats.json"

    with closing(ApsisInstance()) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()

        client = inst.client

        res = client.schedule_adhoc("now", {
            "program": {
                "type": "apsis.program.internal.stats.StatsProgram",
                "path": str(path),
            },
        })
        time.sleep(0.2)
        assert client.get_run(res["run_id"])["state"] == "success"

        res = client.schedule_adhoc("now", {
            "program": {
                "type": "apsis.program.internal.stats.StatsProgram",
                "path": str(path),
            },
        })
        time.sleep(0.2)
        assert client.get_run(res["run_id"])["state"] == "success"

        with open(path) as file:
            stats0 = json.loads(next(file))
            stats1 = json.loads(next(file))
        assert round(ora.Time(stats1["time"]) - ora.Time(stats0["time"]), 1) == 0.2
        assert int(stats0["num_running_tasks"]) == 1
        assert int(stats0["scheduled"]["num_entries"]) == 0
        assert int(stats1["num_running_tasks"]) == 1
        assert int(stats1["scheduled"]["num_entries"]) == 0


