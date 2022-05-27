import asyncio
import time
import threading

import apsis.agent.client

#-------------------------------------------------------------------------------

def go(coro):
    task = asyncio.ensure_future(coro)
    return asyncio.get_event_loop().run_until_complete(task)


def _wait(agent, proc_id):
    # FIXME: Do something better.
    for _ in range(10):
        proc = go(agent.get_process(proc_id))
        if proc["state"] == "run":
            time.sleep(0.1)
        else:
            break
    else:
        assert False, "proc failed to complete in 1 s"

    output = go(agent.get_process_output(proc_id))
    stop = go(agent.del_process(proc_id))

    return proc, output, stop


def test_start_stop():
    agent = apsis.agent.client.Agent()
    go(agent.connect())

    proc_id = go(agent.start_process(["/bin/echo", "Hello, world!"]))["proc_id"]
    proc, output, stop = _wait(agent, proc_id)
    assert proc["state"] == "done"
    assert proc["status"] == 0
    assert proc["return_code"] == 0
    assert proc["signal"] is None
    assert output == b"Hello, world!\n"
    assert stop

    go(agent.stop())

    assert not go(agent.is_running())


def test_connect():
    """
    Tests that a second agent client will connect to the same running agent.
    """
    agent0 = apsis.agent.client.Agent()
    conn0 = go(agent0.connect())

    agent1 = apsis.agent.client.Agent()
    conn1 = go(agent1.connect())

    # Should be the same.
    assert conn1 == conn0

    proc_id0 = go(agent0.start_process(["/bin/echo", "Hello, 0!"]))["proc_id"]
    proc_id1 = go(agent1.start_process(["/bin/echo", "Hello, 1!"]))["proc_id"]

    proc, output, stop = _wait(agent0, proc_id0)
    assert proc["status"] == 0
    assert output == b"Hello, 0!\n"
    assert not stop

    proc, output, stop = _wait(agent1, proc_id1)
    assert proc["status"] == 0
    assert output == b"Hello, 1!\n"
    assert stop

    go(agent0.stop())

    assert not go(agent0.is_running())
    assert not go(agent1.is_running())


def test_concurrent_start():
    """
    Checks that concurrent agent starts all use the same agent.
    """
    agents = [ apsis.agent.client.Agent() for _ in range(10) ]
    res = go(asyncio.gather(*( a.connect() for a in agents )))
    assert len(res) == len(agents)

    # All connections should be to the same port.
    port, _ = res[0]
    assert all( p == port for p, _ in res )

    go(agents[0].stop())

    # All should be stopped.
    res = go(asyncio.gather(*( a.is_running() for a in agents )))
    assert len(res) == len(agents)
    assert all( not r for r in res )


