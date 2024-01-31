from   contextlib import closing, contextmanager
import logging
import os
from   pathlib import Path
from   procstar.agent.testing import get_procstar_path, TLS_CERT_PATH
import secrets
import signal
import subprocess
import uuid

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

AGENT_PORT = 59790

ENV = {
    "PROCSTAR_AGENT_CERT": TLS_CERT_PATH,
    "PROCSTAR_AGENT_TOKEN": secrets.token_urlsafe(32),
}

@contextmanager
def procstar_agent(*, group_id="default"):
    conn_id = str(uuid.uuid4())
    argv = [
        get_procstar_path(),
        "--agent",
        "--agent-host", "localhost",
        "--agent-port", str(AGENT_PORT),
        "--group-id", group_id,
        "--conn-id", conn_id,
        "--connect-interval-start", "0.1",
        "--connect-interval-max", "0.1",
    ]
    env = os.environ | ENV | {
        "RUST_BACKTRACE": "1",
    }
    proc = subprocess.Popen(argv, env=env)
    try:
        yield conn_id
    finally:
        proc.send_signal(signal.SIGKILL)
        proc.wait()


@contextmanager
def apsis_inst():
    job_dir = Path(__file__).parent / "jobs"
    with closing(ApsisInstance(job_dir=job_dir, env=ENV)) as inst:
        inst.create_db()
        inst.write_cfg({
            "procstar": {
                "agent": {
                    "enable": True,
                    "server": {
                        "port": AGENT_PORT,
                    },
                    "connection": {
                        "reconnect_timeout": 5,
                    },
                },
            },
        })
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


def test_program():
    with procstar_agent(), apsis_inst() as inst:
        run_id = inst.client.schedule("sleep", {"time": 1})["run_id"]
        res = inst.wait_run(run_id, timeout=5)
        assert res["state"] == "success"


def test_reconnect():
    """
    Tests reconnecting to a running run after Apsis restart.
    """
    with procstar_agent(), apsis_inst() as inst:
        run_id = inst.client.schedule("sleep", {"time": 1})["run_id"]
        # Wait for the run to start; we can't reconnect to starting runs.
        res = inst.wait_run(run_id, wait_states=("starting", ))
        assert res["state"] == "running"

        inst.restart()

        res = inst.wait_run(run_id, timeout=5)
        assert res["state"] == "success"


def test_reconnect_many():
    """
    Tests reconnecting to many running runs after Apsis restart.
    """
    N = 256

    with procstar_agent(), apsis_inst() as inst:
        run_ids = [
            inst.client.schedule("sleep", {"time": 1})["run_id"]
            for _ in range(N)
        ]
        # Wait for the runs to start; we can't reconnect to starting runs.
        for run_id in run_ids:
            res = inst.wait_run(run_id, wait_states=("starting", ))
            assert res["state"] == "running"

        inst.restart()

        for run_id in run_ids:
            res = inst.wait_run(run_id, timeout=5)
            assert res["state"] == "success"


# FIXME:
# - check that procstar has no undeleted runs at shutdown
# - signal tests
# - procstar connection timeout and reconnect (SIGHUP)

