import asyncio

import apsis.program

#-------------------------------------------------------------------------------

import logging
logging.basicConfig(level=logging.DEBUG)

def go(coro):
    return asyncio.get_event_loop().run_until_complete(
        asyncio.ensure_future(coro))


async def _run():
    prog = apsis.program.AgentProgram(["/bin/sleep", "0.1"])

    # Start the program.
    running, coro = await prog.start("testrun", cfg={})

    # Wait for it to finish.
    result = await coro
    return result


def test_agent_program_basic():
    result = go(_run())
    assert result.meta["status"] == 0


def test_agent_program_concurrent():
    results = go(asyncio.gather(*( _run() for _ in range(16) )))
    assert all( r.meta["status"] == 0 for r in results )


