import asyncio
import pytest
import subprocess

import apsis.lib.asyn

#-------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_communicate_notimeout():
    argv = ["/bin/bash", "-c", "echo foo; echo bar >&2; sleep 0.1"]

    async def no_timeout():
        """
        Non-timeout case.
        """
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await apsis.lib.asyn.communicate(proc, 0.5)

    out, err = await no_timeout()
    assert out == b"foo\n"
    assert err == b"bar\n"


@pytest.mark.asyncio
async def test_communicate_timeout():
    argv = ["/bin/bash", "-c", "echo foo; echo bar >&2; sleep 0.25"]

    async def timeout():
        """
        Timeout case.
        """
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return await apsis.lib.asyn.communicate(proc, 0.1)

    try:
        await timeout()
    except asyncio.TimeoutError as exc:
        assert exc.stdout == b"foo\n"
        assert exc.stderr == b"bar\n"
    else:
        assert False, "should have timed out"

