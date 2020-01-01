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

# class RunStore:

#     def __init__(self, redis):
#         self.__redis = redis


#     async def update(self, run):
#         val = ujson.dumps(run_to_jso(run))



#-------------------------------------------------------------------------------

async def run_to_redis(run, redis):
    key = f"apsis.runs.{run.run_id}".encode()
    await redis.set(key, ujson.dumps(run_to_jso(run)).encode())


async def runs_to_redis(run_db, redis):
    runs = run_db.query()

    with progress.bar.Bar("to Redis", max=len(runs)) as bar:
        async def upload(run):
            await run_to_redis(run, redis)
            bar.next()

        await asyncio.gather(*( upload(r) for r in runs ))


async def upload(db):
    redis = await aioredis.create_redis_pool("redis://localhost")
    await runs_to_redis(db.run_db, redis)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "db", default="apsis.db")
    args = parser.parse_args()

    db = apsis.sqlite.SqliteDB.open(args.db)
    asyncio.run(upload(db))


if __name__ == "__main__":
    main()

