import asyncio
from   contextlib import contextmanager, suppress

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


#-------------------------------------------------------------------------------

class Publisher:
    """
    Manages multiple filtered subscriptions to a publication stream.
    """

    _END = object()

    def __init__(self):
        # Current subscriptions.
        self.__subs = set()


    class Subscription:
        """
        Async iterable and iterator of events sent to one subscription.
        """

        def __init__(self, predicate):
            self.__predicate = predicate
            self.__msgs = asyncio.Queue()
            self.__ended = False


        def publish(self, msg):
            if self.__predicate is None or self.__predicate(msg):
                self.__msgs.put_nowait(msg)


        def _end(self):
            self.__msgs.put_nowait(Publisher._END)


        @property
        def ended(self):
            return self.__ended


        @property
        def len_queue(self):
            return self.__msgs.qsize()


        def __aiter__(self):
            return self


        def __anext__(self):
            if self.__ended:
                raise StopAsyncIteration()
            msg = self.__msgs.get()
            if msg is Publisher._END:
                self.__ended = True
                raise StopAsyncIteration()
            else:
                return msg


        def drain(self):
            """
            Returns all available elements, without waiting.
            """
            msgs = []
            while not self.__ended:
                try:
                    msg = self.__msgs.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    if msg is Publisher._END:
                        self.__ended = True
                    else:
                        msgs.append(msg)
            return msgs



    @contextmanager
    def subscription(self, *, predicate=None):
        """
        Context manager for a subscription.

        :param predicate:
          Predicate function to apply to published messages for inclusion in
          this subscription, or none for all messages.
        """
        if not (predicate is None or callable(predicate)):
            raise TypeError("predicate must be none or callable")

        subscription = self.Subscription(predicate)
        # Register the subscription.
        self.__subs.add(subscription)
        try:
            yield subscription
        finally:
            # Unregister the subscription.
            self.__subs.remove(subscription)


    def publish(self, msg):
        for sub in self.__subs:
            sub.publish(msg)


    def end(self):
        for sub in self.__subs:
            sub._end()


    @property
    def num_queues(self):
        return len(self.__subs)


    @property
    def len_queues(self):
        return sum( s.len_queue for s in self.__subs )



