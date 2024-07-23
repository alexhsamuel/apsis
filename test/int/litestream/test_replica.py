from   contextlib import closing
import os
from   pathlib import Path
import pytest
import shutil
import signal
import subprocess
from   time import sleep

from   instance import ApsisService

JOB_DIR = Path(__file__).parent / "jobs"

# -------------------------------------------------------------------------------

def is_litestream_available():
    return shutil.which("litestream") is not None


def start_litestream(db_path, replica_path):
    return subprocess.Popen(
        [
            "litestream",
            "replicate",
            db_path,
            f"file://{str(replica_path)}",
        ]
    )


def restore_litestream_db(restored_db_path, litestream_replica_path):
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


@pytest.mark.skipif(not is_litestream_available(), reason="Litestream is not available")
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

        with start_litestream(
                inst.db_path, litestream_replica_path
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
                assert client.get_run(run_id)["state"] == "success"
                if state != "success":
                    client.mark(run_id, state)
                run_ids.append(run_id)

            # stop Apsis and Litestream
            inst.stop_serve()
            litestream_process.terminate()

        # restore the db from the replica
        restored_db_name = "restored.db"
        restored_db_path = inst.tmp_dir / restored_db_name

        restore_litestream_db(restored_db_path, litestream_replica_path)

        # rewrite the config to use restored db
        inst.db_path = restored_db_path
        inst.write_cfg()

        # restart Apsis
        inst.start_serve()
        inst.wait_for_serve()

        log = inst.get_log_lines()
        assert any(restored_db_name in l for l in log)

        # check runs data is accurate in the restored db
        for id, state in zip(run_ids, expected_states):
            assert client.get_run(id)["state"] == state

        # run job again to verify the db is in a good state and Apsis can read/write it
        new_run_id = client.schedule("job1", {})["run_id"]
        inst.wait_run(new_run_id)
        assert client.get_run(new_run_id)["state"] == "success"

        inst.stop_serve()


@pytest.mark.skipif(not is_litestream_available(), reason="Litestream is not available")
def test_replica_killing_apsis_and_litestream():
    """
    Similar to `test_replica`, but here:
    - Apsis and Litestream processes are terminated with SIGKILL signal;
    - Apsis is killed while there is still a run in the running state;

    Steps:
    - start Litestream process;
    - start Apsis and schedule a run;
    - kill Apsis and Litestream using SIGKILL signals;
    - restore db from Litestream replica;
    - check that the run is still in running state using the restored db.
    """
    with closing(ApsisService(job_dir=JOB_DIR)) as inst:
        inst.create_db()
        inst.write_cfg()

        # start Litestream replica
        litestream_replica_path = inst.tmp_dir / "litestream_replica.db"

        with start_litestream(
            inst.db_path, litestream_replica_path
        ) as litestream_process:
            inst.start_serve()
            inst.wait_for_serve()

            client = inst.client
            run_id = client.schedule("job1", {})["run_id"]

            # stop Apsis and Litestream
            sleep(1)
            os.kill(inst.srv_proc.pid, signal.SIGKILL)
            sleep(1)
            os.kill(litestream_process.pid, signal.SIGKILL)

        # restore the db from the replica
        restored_db_name = "restored.db"
        restored_db_path = inst.tmp_dir / restored_db_name
        restore_litestream_db(restored_db_path, litestream_replica_path)

        # rewrite the config to use restored db
        inst.db_path = restored_db_path
        inst.write_cfg()

        # restart Apsis
        inst.srv_proc = None
        inst.start_serve()
        inst.wait_for_serve()

        log = inst.get_log_lines()
        assert any(restored_db_name in l for l in log)

        # check the run is still in the running state after reconnecting to the new Apsis instance
        assert client.get_run(run_id)["state"] == "running"

        # check run eventually completes successfully
        inst.wait_run(run_id)
        assert client.get_run(run_id)["state"] == "success"

        inst.stop_serve()


