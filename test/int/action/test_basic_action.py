from   contextlib import closing
from   pathlib import Path
import pytest

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

job_dir = Path(__file__).absolute().parent / "jobs"

@pytest.fixture(scope="function")
def inst():
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


def test_run_action(inst):
    run_id = inst.client.schedule("with snapshot", {})["run_id"]
    inst.wait_run(run_id)
    log = inst.get_log_lines()

    # There should be a log line with the run ID.
    token = f"run ID: {run_id}"
    assert any( token in l for l in log )

    # There should be a log line with the output.
    assert any( "output: Hello, world!" in l for l in log )



