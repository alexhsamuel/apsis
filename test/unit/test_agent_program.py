import asyncio
import pytest

import apsis.program

#-------------------------------------------------------------------------------

async def _run():
    prog = apsis.program.AgentProgram(["/bin/sleep", "0.1"])

    # Start the program.
    running, coro = await prog.start("testrun", cfg={})

    # Wait for it to finish.
    result = await coro
    return result


@pytest.mark.asyncio
async def test_agent_program_basic():
    result = await _run()
    assert result.meta["status"] == 0


@pytest.mark.asyncio
async def test_agent_program_concurrent():
    results = await asyncio.gather(*( _run() for _ in range(16) ))
    assert all( r.meta["status"] == 0 for r in results )


