from   contextlib import closing
from   pathlib import Path
import pytest

from   instance import ApsisInstance

#-------------------------------------------------------------------------------

job_dir = Path(__file__).absolute().parent / "schedule-jobs"

@pytest.fixture(scope="function")
def inst():
    with closing(ApsisInstance(job_dir=job_dir)) as inst:
        inst.create_db()
        inst.write_cfg()
        inst.start_serve()
        inst.wait_for_serve()
        yield inst


def test_schedule_action(inst):
    client = inst.client

    r1 = client.schedule("first", {"label": "foo"})["run_id"]
    # There should be only one one right now.
    assert { r["run_id"] for r in client.get_runs().values() } == {r1}

    inst.wait_run(r1)

    run, = tuple(client.get_runs(job_id="second").values())
    assert run["args"] == {"label": "on-success"}

    runs = tuple(client.get_runs(job_id="third").values())
    assert len(runs) == 0

    runs = tuple(client.get_runs(job_id="fourth").values())
    assert len(runs) == 1

    run, = tuple(client.get_runs(job_id="fifth").values())
    assert run["args"] == {"label": "foo"}


