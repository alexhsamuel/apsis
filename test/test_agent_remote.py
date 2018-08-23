import asyncio
from   pathlib import Path

from   apsis.agent.client import Agent

#-------------------------------------------------------------------------------

def go(coro):
    task = asyncio.ensure_future(coro)
    return asyncio.get_event_loop().run_until_complete(task)


def test_run_localhost(tmpdir):
    path = Path(tmpdir) / "output.txt"
    assert not path.is_file()

    agent = Agent(host="localhost")

    async def run():
        process = await agent.start_process(
            ["/bin/bash", "-c", f"echo 'Hello, world!' > '{path}'"])
        proc_id = process["proc_id"]
        # FIXME: Embarrassing.  Need a way to await the process.
        await asyncio.sleep(0.1)
        process = await agent.get_process(proc_id)
        output = await agent.get_process_output(proc_id)
        await agent.del_process(proc_id)
        return process["return_code"], output

    return_code, output = go(run())
    assert return_code == 0
    assert output == b""
    assert path.is_file()
    with open(path, "rt") as file:
        data = file.read()
    assert data == "Hello, world!\n"


