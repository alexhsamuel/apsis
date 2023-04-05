import argparse
import ora
from   pathlib import Path
import random
import sys
import yaml

#-------------------------------------------------------------------------------

PROB_DURATION = 0.1

PROB_INTERVAL = 0.25
PROB_FREQUENT = 0.05
MAX_SCHEDULED_DAILY = 288

MAX_JOB_ID_DEPTH = 3

LABELS = ("foo", "bar", "baz", "bif")

PROB_ARG = 0.05
ARGS = {
    "fruit": ("apple", "pear", "kiwi", "mango"),
    "hue": ("red", "blue", "green", "yellow"),
}

#--------------------------------------------------------------------------------

def random_daytime():
    return str(ora.Daytime.from_ssm(random.randint(0, 86399)))


def gen_duration():
    r = random.random()
    return (
        0 if r < 0.50
        else random.randint(1, 60) if r < 0.95
        else random.randint(1, 180) * 60  # up to 3 hours
    )


OUTPUT_SCRIPT = """
import random, string, sys, time
lines, length, delay = sys.argv[1 :]
length = int(length)
delay = float(delay)
for _ in range(int(lines)):
    print("".join( random.choice(string.ascii_letters) for _ in range(length) ))
    time.sleep(delay)
"""

def gen_output_program():
    lines = random.randint(1, 10000)
    length = random.randint(8, 78)
    delay = round(random.random() * 0.1, 4)
    return {
        "type": "program",
        "argv": [
            sys.executable, "-c", OUTPUT_SCRIPT,
            str(lines), str(length), str(delay),
        ],
    }


def gen_program():
    r = random.random()
    if r < 0.99:
        return {
            "type": "no-op",
            "duration": str(gen_duration()),
        }

    else:
        return gen_output_program()


def gen_job():
    params = []

    labels = list({
        random.choice(LABELS)
        for _ in range(int(random.uniform(0, 2) ** 2))
    })

    program = gen_program()

    count = (
        random.randint(1, MAX_SCHEDULED_DAILY)
        if random.random() < PROB_FREQUENT
        else 1
    )

    if random.random() < PROB_INTERVAL:
        # Interval schedule.
        schedule = {
            "type": "interval",
            "interval": 86400 // count,
        }
    else:
        schedule = {
            "type": "daily",
            "tz": "UTC",
            "daytime": sorted( random_daytime() for _ in range(count) )
        }
        params.append("date")

    for param, args in ARGS.items():
        if random.random() < PROB_ARG:
            params.append(param)
            schedule.setdefault("args", {})[param] = random.choice(args)

    return {
        "metadata": {
            "labels": labels,
        },
        "params": params,
        "program": program,
        "schedule": schedule,
    }


def gen_job_id():
    return "/".join((
        *(
            f"group{random.randint(0, 100)}"
            for _ in range(random.randint(0, MAX_JOB_ID_DEPTH))
        ),
        f"job{random.randint(0, 100000)}"
    ))


#--------------------------------------------------------------------------------

parser = argparse.ArgumentParser()
parser.add_argument(
    "num", metavar="NUM", type=int,
    help="generate NUM jobs")
parser.add_argument(
    "--output", metavar="DIR", type=Path, default=Path("./jobs"),
    help="generate to DIR [def: ./jobs]")
args = parser.parse_args()

for _ in range(args.num):
    job = gen_job()
    job_id = gen_job_id()
    path = (args.output / job_id).with_suffix(".yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        yaml.dump(job, file)

