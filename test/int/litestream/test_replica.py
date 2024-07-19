from pathlib import Path
from contextlib import closing
import subprocess

from instance import ApsisService


JOB_DIR = Path(__file__).parent / "jobs"

# -------------------------------------------------------------------------------


def test_replica():
    """
    Tests Litestream replica of the SQLite db.

    Steps:
    - start Litestream process;
    - start Apsis and populate its db with some data;
    - stop Apsis (i.e. simulating a db failure) and Litestream processes;
    - restore db from Litestream replica;
    - check that Apsis works fine with the restored db and that data initially written to the original db are there.
    """

    with closing(ApsisService(job_dir=JOB_DIR)) as inst:

        inst.create_db()
        inst.write_cfg()

        # start Litestream replica
        litestream_replica_path = inst.tmp_dir / "litestream_replica.db"
        with subprocess.Popen(
            [
                "litestream",
                "replicate",
                inst.db_path,
                f"file://{str(litestream_replica_path)}",
            ]
        ) as litestream_process:

            inst.start_serve()
            inst.wait_for_serve()

            # populate apsis db with some data
            client = inst.client
            run_ids = []
            expected_states = ["success", "failure", "error", "skipped"]
            for state in expected_states:
                run_id = client.schedule("job1", {})["run_id"]
                inst.wait_run(run_id)
                if state != "success":
                    client.mark(run_id, state)
                run_ids.append(run_id)

            # stop Apsis and Litestream
            inst.stop_serve()
            litestream_process.terminate()

        # restore the db from the replica
        restored_db_name = "restored.db"
        restored_db_path = inst.tmp_dir / restored_db_name
        subprocess.run(
            [
                "litestream",
                "restore",
                "-o",
                str(restored_db_path),
                f"file://{str(litestream_replica_path)}",
            ],
            check=True,
        )

        # rewrite the config to use restored db
        inst.db_path = restored_db_path
        inst.write_cfg()

        # restart Apsis
        inst.start_serve()
        inst.wait_for_serve()

        log = inst.get_log_lines()
        assert any(restored_db_name in l for l in log)

        # check runs data is accurate in the restored db
        client = inst.client
        for id, state in zip(run_ids, expected_states):
            assert client.get_run(id)["state"] == state

        # run job again to verify the db is in a good state and Apsis can read/write it
        new_run_id = client.schedule("job1", {})["run_id"]
        inst.wait_run(new_run_id)
        assert client.get_run(new_run_id)["state"] == "success"

        inst.stop_serve()
