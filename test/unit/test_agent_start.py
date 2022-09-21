import asyncio
import time
import threading
import pytest

import apsis.agent.client

#-------------------------------------------------------------------------------

async def _wait(agent, proc_id):
    # FIXME: Do something better.
    for _ in range(10):
        proc = await agent.get_process(proc_id)
        if proc["state"] == "run":
            time.sleep(0.1)
        else:
            break
    else:
        assert False, "proc failed to complete in 1 s"

    output = await agent.get_process_output(proc_id)
    stop = await agent.del_process(proc_id)

    return proc, output, stop


@pytest.mark.asyncio
async def test_start_stop():
    agent = apsis.agent.client.Agent()
    await agent.connect()

    proc_id = (await agent.start_process(["/bin/echo", "Hello, world!"]))["proc_id"]
    proc, output, stop = await _wait(agent, proc_id)
    assert proc["state"] == "done"
    assert proc["status"] == 0
    assert proc["return_code"] == 0
    assert proc["signal"] is None
    assert output == b"Hello, world!\n"
    assert stop

    await agent.stop()

    assert not await agent.is_running()


@pytest.mark.asyncio
async def test_connect():
    """
    Tests that a second agent client will connect to the same running agent.
    """
    agent0 = apsis.agent.client.Agent()
    conn0 = await agent0.connect()

    agent1 = apsis.agent.client.Agent()
    conn1 = await agent1.connect()

    # Should be the same.
    assert conn1 == conn0

    proc_id0 = (await agent0.start_process(["/bin/echo", "Hello, 0!"]))["proc_id"]
    proc_id1 = (await agent1.start_process(["/bin/echo", "Hello, 1!"]))["proc_id"]

    proc, output, stop = await _wait(agent0, proc_id0)
    assert proc["status"] == 0
    assert output == b"Hello, 0!\n"
    assert not stop

    proc, output, stop = await _wait(agent1, proc_id1)
    assert proc["status"] == 0
    assert output == b"Hello, 1!\n"
    assert stop

    await agent0.stop()

    assert not await agent0.is_running()
    assert not await agent1.is_running()


@pytest.mark.asyncio
async def test_concurrent_start():
    """
    Checks that concurrent agent starts all use the same agent.
    """
    agents = [ apsis.agent.client.Agent() for _ in range(10) ]
    res = await asyncio.gather(*( a.connect() for a in agents ))
    assert len(res) == len(agents)

    # All connections should be to the same port.
    port, _ = res[0]
    assert all( p == port for p, _ in res )

    await agents[0].stop()

    # All should be stopped.
    res = await asyncio.gather(*( a.is_running() for a in agents ))
    assert len(res) == len(agents)
    assert all( not r for r in res )


