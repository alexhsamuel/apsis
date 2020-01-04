import aioredis
import asyncio
import progress.bar
import ujson

import apsis.sqlite

#-------------------------------------------------------------------------------
# FIXME: These should be part of Run, and merge with apsis.service.api.

from   apsis.lib.api import time_to_jso

def run_to_jso(run):
    conds = [] if run.conds is None else run.conds
    return {
        "job_id"        : run.inst.job_id,
        "args"          : run.inst.args,
        "run_id"        : run.run_id,
        "timestamp"     : time_to_jso(run.timestamp),
        "state"         : run.state.name,
        "conds"         : [ c.to_jso() for c in conds ],
        "program"       : None if run.program is None else run.program.to_jso(),
        "times"         : { n: time_to_jso(t) for n, t in run.times.items() },
        "meta": run.meta,
        "message"       : run.message,
        "time_range"    : None if len(run.times) == 0 else [
            time_to_jso(min(run.times.values())),
            time_to_jso(max(run.times.values())),
        ],
        "run_state"     : run.run_state,
        "rerun"         : run.rerun,
        "expected"      : run.expected,
    }


#-------------------------------------------------------------------------------

class RunStore:

    def __init__(self, redis):
        self.__redis = redis


    @staticmethod
    def get_run_key(run):
        return f"apsis.runs.{run.run_id}".encode()


    def update(self, run):
        """
        Returns a run update coro.
        """
        jso = ujson.dumps(run_to_jso(run))

        tx = self.__redis.multi_exec()
        tx.set(self.get_run_key(run), jso)
        tx.publish("apsis.runs", jso)
        return tx.execute()


    async def watch_all(self):
        channel, = await self.__redis.subscribe("apsis.runs")
        async for msg in channel.iter():
            yield ujson.decode(msg)



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


async def run_to_redis(run, redis):
    key = f"apsis.runs.{run.run_id}".encode()
    await redis.set(key, ujson.dumps(run_to_jso(run)).encode())


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
    async for r in run_jsos:
        run_id  = r["run_id"]
        state   = r["state"]
        job_id  = r["job_id"]
        args    = " ".join( f"{k}={v}" for k, v in r["args"].items() )
        print(f"{run_id} {state:10s}: {job_id} {args}")


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

