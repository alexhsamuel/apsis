import aioredis
import asyncio
import progress.bar
import ujson

#-------------------------------------------------------------------------------

class RunStore:

    def __init__(self, redis):
        self.__redis = redis


    @staticmethod
    def get_run_key(run_id):
        return f"apsis.runs.{run_id}".encode()


    # async
    def update(self, run):
        """
        :return:
          A coro.
        """
        json = ujson.dumps(run.to_jso())

        tx = self.__redis.multi_exec()
        tx.set(self.get_run_key(run.run_id), json)
        tx.publish("apsis.runs.update", json)
        return tx.execute()


    # async
    def delete(self, run):
        """
        :return:
          A coro.
        """
        json = ujson.dumps(run.to_jso())

        tx = self.__redis.multi_exec()
        tx.delete(self.get_run_key(run.run_id))
        tx.publish("apsis.runs.delete", json)
        return tx.execute()


    async def watch_all(self):
        channel, = await self.__redis.psubscribe("apsis.runs.*")
        async for name, json in channel.iter():
            assert name.startswith(b"apsis.runs.")
            cmd = name[11 :].decode()
            jso = ujson.decode(json)
            yield cmd, jso



#-------------------------------------------------------------------------------

async def progress_gather(bar, coros):
    """
    Gathers `coros` with progress `bar`.
    """
    next = lambda _: bar.next()

    def setup(coro):
        fut = asyncio.ensure_future(coro)
        fut.add_done_callback(next)
        return fut

    with bar:
        return await asyncio.gather(*( setup(c) for c in coros ))


# FIXME: Remove; use run store.
async def run_to_redis(run, redis):
    key = f"apsis.runs.{run.run_id}".encode()
    await redis.set(key, ujson.dumps(run.to_jso()).encode())


#-------------------------------------------------------------------------------

async def upload(db):
    redis = await aioredis.create_redis_pool("redis://localhost")
    runs = db.run_db.query()
    with progress.bar.Bar(max=len(runs)) as bar:
        await progress_gather(bar, ( run_to_redis(r, redis) for r in runs ))


async def watch_all():
    redis = await aioredis.create_redis_pool("redis://localhost")
    run_store = RunStore(redis)
    run_jsos = run_store.watch_all()
    async for cmd, r in run_jsos:
        run_id  = r["run_id"]
        state   = r["state"]
        job_id  = r["job_id"]
        args    = " ".join( f"{k}={v}" for k, v in r["args"].items() )
        print(f"{cmd} {run_id} {state:10s}: {job_id} {args}")


def main():
    import apsis.lib.argparse
    parser = apsis.lib.argparse.CommandArgumentParser()

    def cmd_upload(args):
        db = apsis.sqlite.SqliteDB.open(args.db)
        asyncio.run(upload(db))

    cmd = parser.add_command("upload", cmd_upload)
    cmd.add_argument("db", default="apsis.db")

    def cmd_watch_all(args):
        asyncio.run(watch_all())

    cmd = parser.add_command("watch-all", cmd_watch_all)

    args = parser.parse_args()
    args.cmd(args)


if __name__ == "__main__":
    main()

