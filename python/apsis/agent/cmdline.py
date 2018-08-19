import argparse
import asyncio
import json
import sys

from   apsis.agent.client import Agent

#-------------------------------------------------------------------------------

def sync(coro):
    task = asyncio.ensure_future(coro)
    asyncio.get_event_loop().run_until_complete(task)
    return task.result()


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(title="commands")
    parser.set_defaults(cmd=None)

    cmd = commands.add_parser("list")
    cmd.set_defaults(cmd="list")

    cmd = commands.add_parser("get")
    cmd.add_argument("proc_id")
    cmd.set_defaults(cmd="get")

    cmd = commands.add_parser("del")
    cmd.add_argument("proc_id")
    cmd.set_defaults(cmd="del")

    cmd = commands.add_parser("shut_down")
    cmd.set_defaults(cmd="shut_down")

    args = parser.parse_args()
    agent = Agent(start=False)  # FIXME: Who, where?

    if args.cmd is None:
        parser.error("no command given")
    elif args.cmd == "list":
        result = agent.get_processes()
    elif args.cmd == "get":
        result = agent.get_process(args.proc_id)
    elif args.cmd == "del":
        result = agent.del_process(args.proc_id)
    elif args.cmd == "shut_down":
        result = agent.shut_down()

    try:
        result = sync(result)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
    else:
        json.dump(result, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()

