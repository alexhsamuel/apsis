#!/usr/bin/python3 -u

import os
import sys

def main():
    for i, arg in enumerate(sys.argv):
        print("argv[{}] = {!r}".format(i, arg))
    print()

    for name, value in os.environ.items():
        print("env[{}] = {!r}".format(name, value))
    print()

    stdin = sys.stdin.read();
    print("stdin:", repr(stdin))

    print("to stdout", file=sys.stdout)
    print("to stderr", file=sys.stderr)
    print("to stdout", file=sys.stdout)
    print("to stderr", file=sys.stderr)

    print("end of program")
    raise SystemExit(42)


if __name__ == "__main__":
    main()

