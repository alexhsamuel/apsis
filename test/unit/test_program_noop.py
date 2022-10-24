import time
import pytest

import apsis.program

#-------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duration():
    JSO = {
        "type": "no-op",
        "duration": "0.75",
    }

    prog = apsis.program.Program.from_jso(JSO)
    start = time.monotonic()
    running, coro = await prog.start("testrun", cfg={})
    result = await coro
    elapsed = time.monotonic() - start
    assert elapsed > 0.75


