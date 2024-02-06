from   contextlib import closing
import pytest
import sqlite3
import time

from   apsis.service.client import APIError
from   instance import ApsisService

#-------------------------------------------------------------------------------

def test_archive(tmp_path):
    path = tmp_path / "archive.db"

    with closing(ApsisService(cfg={"schedule": {"horizon": 1}})) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()

        client = inst.client

        # Run two runs, wait 2 s, then run another.

        res = client.schedule_adhoc("now", {"program": {"type": "no-op"}})
        run_id0 = res["run_id"]
        res = client.schedule_adhoc(
            "now",
            {
                "program": {
                    "type": "shell",
                    "command": "echo 'Hello, world!'",
                }
            }
        )
        run_id1 = res["run_id"]

        time.sleep(2)

        res = client.schedule_adhoc("now", {"program": {"type": "no-op"}})
        run_id2 = res["run_id"]

        # Archive, with a max age of 2 s and up to 1 run.
        res = client.schedule_adhoc("now", {
            "program": {
                "type": "apsis.program.internal.archive.ArchiveProgram",
                "age": 2,
                "count": 1,
                "path": str(path),
            },
        })
        res = inst.wait_run(res["run_id"])
        # The first run has been archived.
        assert res["meta"]["run count"] == 1
        assert res["meta"]["run_ids"] == [run_id0]

        # The first run is no longer be available; the other two are.
        with pytest.raises(APIError):
            client.get_run(run_id0)
        assert client.get_run(run_id1)["state"] == "success"
        assert client.get_run(run_id2)["state"] == "success"

        # Archive, with a max age of 2 s.
        time.sleep(0.5)
        res = client.schedule_adhoc("now", {
            "program": {
                "type": "apsis.program.internal.archive.ArchiveProgram",
                "age": 2,
                "count": 10,
                "path": str(path),
            },
        })
        # The second run was archived, but the third isn't old enough yet.
        res = inst.wait_run(res["run_id"])
        assert res["meta"]["run count"] == 1
        assert res["meta"]["run_ids"] == [run_id1]

        # The second run is no longer available.
        with pytest.raises(APIError):
            client.get_run(run_id1)
        assert client.get_run(run_id2)["state"] == "success"

        # Check the archive file.
        with closing(sqlite3.connect(path)) as db:
            rows = list(db.execute("SELECT run_id, state FROM runs"))
            assert rows == [
                (run_id0, "success"),
                (run_id1, "success"),
            ]

            rows = list(db.execute(
                "SELECT message FROM run_history WHERE run_id = ?", (run_id0, )))
            assert "scheduled: now" in rows[0][0]
            assert "success" in rows[-1][0]

            rows = list(db.execute("SELECT run_id, name, length FROM output"))
            # Only the second run had output.
            assert len(rows) == 1
            assert rows[0] == (run_id1, "combined stdout & stderr", 14)


