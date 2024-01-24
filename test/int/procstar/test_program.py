from   contextlib import closing
import os
from   pathlib import Path
from   procstar.agent.testing import get_procstar_path, TLS_CERT_PATH
import pytest
import secrets
import signal
import subprocess
import uuid

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

ENV = {
    "PROCSTAR_AGENT_CERT": TLS_CERT_PATH,
    "PROCSTAR_AGENT_TOKEN": secrets.token_urlsafe(32),
}

@pytest.fixture(scope="function")
def procstar(*, group_id="default"):
    conn_id = str(uuid.uuid4())
    argv = [
        get_procstar_path(),
        "--agent",
        "--agent-host", "localhost",
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
        proc.send_signal(signal.SIGTERM)
        proc.wait()


@pytest.fixture(scope="function")
def inst():
    job_dir = Path(__file__).parent / "jobs"
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg({
            "procstar": {
                "agent": {
                    "enable": True,
                },
            },
        })
        inst.start_serve(env=ENV)
        inst.wait_for_serve()
        yield inst


def test_program(procstar, inst):
    run_id = inst.client.schedule("sleep", {"time": 1})["run_id"]
    res = inst.wait_run(run_id, timeout=5)
    assert res["state"] == "success"


