import asyncio
import time

import apsis.agent.client

#-------------------------------------------------------------------------------

def go(coro):
    task = asyncio.ensure_future(coro)
    return asyncio.get_event_loop().run_until_complete(task)


def test_start_stop():
    agent = apsis.agent.client.Agent()
    go(agent.start())

    proc_id = go(agent.start_process(["/bin/echo", "Hello, world!"]))["proc_id"]
    # FIXME: Do something better than poll.
    for _ in range(10):
        proc = go(agent.get_process(proc_id))
        if proc["state"] == "run":
            time.sleep(0.1)
        else:
            break

    assert proc["state"] == "done"
    assert proc["status"] == 0
    assert proc["return_code"] == 0
    assert proc["signal"] is None

    output = go(agent.get_process_output(proc_id))
    assert output == b"Hello, world!\n"

    shutdown = go(agent.del_process(proc_id))
    assert shutdown

    assert not go(agent.is_running())


