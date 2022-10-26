import argparse
import math
import ora
from   pathlib import Path
import random
import yaml

#-------------------------------------------------------------------------------

PROB_DURATION = 0.1
MAX_DURATION = 60

PROB_INTERVAL = 0.25
PROB_FREQUENT = 0.05
MAX_SCHEDULED_DAILY = 288

MAX_JOB_ID_DEPTH = 3

#--------------------------------------------------------------------------------

def random_daytime():
    return str(ora.Daytime.from_ssm(random.randint(0, 86399)))

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
    params = []

    program = {
        "type": "no-op",
    }
    if random.random() < PROB_DURATION:
        program["duration"] = str(random.randint(0, MAX_DURATION))

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

    job = {
        "params": params,
        "program": program,
        "schedule": schedule,
    }

    job_id = "/".join((
        *(
            f"group{random.randint(0, 100)}"
            for _ in range(random.randint(0, MAX_JOB_ID_DEPTH))
        ),
        f"job{random.randint(0, 100000)}"
    ))

    path = (args.output / job_id).with_suffix(".yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as file:
        yaml.dump(job, file)

