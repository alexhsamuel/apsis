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

async def cancel_task(task, name=None, log=None):
    """
    Cancels and cleans up `task`, with logging as `name`.
    """
    if task.cancelled():
        if log is not None:
            log.info(f"task already cancelled: {name}")
    else:
        task.cancel()

    try:
        return await task
    except asyncio.CancelledError:
        if log is not None:
            log.info(f"task cancelled: {name}")
    except Exception:
        if log is not None:
            log.error(f"task cancelled with exc: {name}", exc_info=True)


async def poll(fn, interval, immediate=False):
    """
    Invokes async `fn` every `interval`.

    :param immediate:
      Call `fn` immediately, before the first interval.
    """
    if immediate:
        await fn()
    while True:
        await asyncio.sleep(interval)
        await fn()


class TaskGroup:
    """
    Tracks a group of running tasks.

    Each added tasks get a callback that removes itself from the group.
    """

    def __init__(self, log=None):
        self.__tasks = {}
        self.__log = log


    def __len__(self):
        return len(self.__tasks)


    def add(self, key, coro):
        task = asyncio.get_event_loop().create_task(coro)
        task.key = key
        self.__tasks[key] = task
        task.add_done_callback(lambda _, key=key: self.__tasks.pop(key))


    async def cancel(self, key):
        await cancel_task(self.__tasks[key], key, self.__log)


    async def cancel_all(self):
        """
        Cancels all running tasks.
        """
        for key, task in tuple(self.__tasks.items()):
            await cancel_task(task, key, self.__log)



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


