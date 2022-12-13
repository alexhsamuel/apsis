import asyncio
import pytest
import subprocess

import apsis.lib.asyn

#-------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_communicate_notimeout():
    argv = ["/bin/bash", "-c", "echo foo; echo bar >&2; sleep 0.1"]

    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = await apsis.lib.asyn.communicate(proc, 0.5)
    assert out == b"foo\n"
    assert err == b"bar\n"


@pytest.mark.asyncio
async def test_communicate_timeout():
    argv = ["/bin/bash", "-c", "echo foo; echo bar >&2; sleep 0.25"]

    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        await apsis.lib.asyn.communicate(proc, 0.1)
    except asyncio.TimeoutError as exc:
        assert exc.stdout == b"foo\n"
        assert exc.stderr == b"bar\n"
        # Clean up the process, so that it doesn't outlive the event loop.
        await proc.wait()
    else:
        assert False, "should have timed out"


