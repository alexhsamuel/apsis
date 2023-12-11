import asyncio
from   contextlib import suppress

#-------------------------------------------------------------------------------

def _install():
    """
    Monkeypatches the event loop policy to augment new event loops with
    `on_close` behavior.
    """
    policy = asyncio.get_event_loop_policy()
    old_new_event_loop = policy.new_event_loop

    def new_event_loop():
        """
        Monkeypatches a new event loop with an `on_close()` method to
        register awaitables to call on close (in reverse order), and wraps its
        `close()` method to call these.
        """
        loop = old_new_event_loop()
        loop.__on_close = []
        old_close = loop.close

        def on_close(aw):
            loop.__on_close.append(aw)

        def close():
            for aw in reversed(loop.__on_close):
                loop.run_until_complete(aw)
            loop.__on_close.clear()
            return old_close()

        loop.on_close = on_close
        loop.close = close
        return loop

    policy.new_event_loop = new_event_loop
    asyncio.set_event_loop_policy(policy)


_install()

#-------------------------------------------------------------------------------

async def cancel_task(task, name, log):
    """
    Cancels and cleans up `task`, with logging as `name`.
    """
    if task.cancelled():
        log.info(f"task already cancelled: {name}")
    else:
        task.cancel()

    try:
        return await task
    except asyncio.CancelledError:
        log.info(f"task cancelled: {name}")
    except Exception:
        log.error(f"task cancelled with exc: {name}", exc_info=True)


class TaskGroup:

    def __init__(self, log):
        self.__tasks = set()
        self.__log = log


    def add(self, coro, name):
        task = asyncio.ensure_future(coro)
        task.name = name
        self.__tasks.add(task)
        task.add_done_callback(lambda _, task=task: self.__tasks.remove(task))


    async def cancel_all(self):
        for task in self.__tasks:
            await cancel_task(task, task.name, self.__log)



#-------------------------------------------------------------------------------

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


