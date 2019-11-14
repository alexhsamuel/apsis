import asyncio
from   contextlib import suppress

#-------------------------------------------------------------------------------

async def cancel_task(task, name, log):
    """
    Cancels and cleans up `task`, with logging as `name`.
    """
    log.info(f"canceling {name} task")
    if task.cancelled():
        log.info(f"{name} task already canceled")
    else:
        task.cancel()

    try:
        return await task
    except asyncio.CancelledError:
        log.info(f"{name} task canceled")
    except Exception:
        log.error(f"{name} task raised", exc_info=True)


async def communicate(proc, timeout=None):
    """
    Like `proc.communicate` with a timeout.

    Assumes stdout, stderr are piped in binary mode and stdin is not piped.

    :param timeout:
      Timeout in sec, or none for no timeout.
    :raise asyncio.TimeoutError:
      Timed out.  The exception's `stdout` and `stderr` attributes contain
      captured outputs.
    """
    out = []
    err = []

    async def read(stream, chunks, size=1024):
        while True:
            chunk = await stream.read(size)
            if len(chunk) == 0:
                # EOF
                break
            else:
                chunks.append(chunk)

    gathered = asyncio.gather(
        read(proc.stdout, out),
        read(proc.stderr, err),
        proc.wait()
    )

    try:
        await asyncio.wait_for(gathered, timeout)
    except asyncio.TimeoutError as exc:
        with suppress(asyncio.CancelledError):
            await gathered
        exc.stdout = b"".join(out)
        exc.stderr = b"".join(err)
        raise

    return b"".join(out), b"".join(err)


