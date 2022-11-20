from   contextlib import closing
from   pathlib import Path
import pytest
from   time import sleep

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

job_dir = Path(__file__).absolute().parent / "test_output_jobs"

@pytest.fixture(scope="module")
def inst():
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst
 

@pytest.fixture
def client(inst, scope="module"):
    return inst.client


#-------------------------------------------------------------------------------

def test_output(client):
    res = client.schedule("printf", {"string": "hello\n"})
    run_id = res["run_id"]
    # FIXME
    sleep(0.25)
    res = client.get_run(run_id)
    assert res["state"] == "success"

    outputs = client.get_outputs(run_id)
    assert len(outputs) == 1
    assert outputs[0]["output_id"] == "output"  # combined stdout and stderr
    assert outputs[0]["output_len"] == 6

    output = client.get_output(run_id, "output")
    assert output == b"hello\n"


