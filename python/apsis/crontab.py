from   pathlib import Path
import re

from   .job import Job
from   .schedule import CrontabSchedule
from   .program import ShellCommandProgram

#-------------------------------------------------------------------------------

class CrontabSyntaxError(Exception):
    pass


ENVIRONMENT_REGEX = re.compile(r"([A-Za-z_]+)\s*=\s*(.*)$")

MONTH_NAMES = {
    "jan":  1, "feb":  2, "mar":  3, "apr":  4, "may":  5, "jun":  6,
    "jul":  7, "aug":  8, "sep":  9, "oct": 10, "nov": 11, "dec": 12,
}

WEEKDAY_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6,
}

def parse_command(line):
    try:
        minute, hour, day, month, weekday, command = line.split(None, 5)
    except ValueError:
        raise CrontabSyntaxError(line)

    def _parse(string, min, max, names):
        for part in string.split(","):
            try:
                part, step = part.split("/", 1)
            except ValueError:
                step    = 1
            else:
                step    = int(step)
            if part == "*":
                start   = min
                stop    = max
            else:
                try:
                    start, stop = part.split("-", 1)
                except ValueError:
                    start   = int(names.get(part.lower(), part))
                    stop    = start
                else:
                    start   = int(names.get(start.lower(), start))
                    stop    = int(names.get(stop.lower(), stop))
            yield from range(start, stop + 1, step)

    def parse(string, min, max, names={}):
        numbers = sorted(_parse(string, min, max, names))
        if numbers[0] < min or max < numbers[-1]:
            raise CrontabSyntaxError(line)
        return numbers

    minute  = parse(minute, 0, 59)
    hour    = parse(hour, 0, 23)
    day     = parse(day, 1, 31)
    month   = parse(month, 1, 12, MONTH_NAMES)
    weekday = parse(weekday, 0, 6, WEEKDAY_NAMES)

    # FIXME!
    tz = "US/Eastern"

    return CrontabSchedule(tz, minute, hour, day, month, weekday), command
                    


def parse_crontab(id, lines):
    lines = ( l.strip() for l in lines )
    lines = ( l for l in lines if len(l) > 0 and l[0] != "#" )

    environment = {}
    jobs = []
    for line in lines:
        match = re.match(ENVIRONMENT_REGEX, line)
        if match is not None:
            environment[match.group(1)] = match.group(2)
        else:
            schedule, command = parse_command(line)
            jobs.append(Job(
                job_id  ="{}-{}".format(id, len(jobs)),
                schedule=schedule,
                program =ShellCommandProgram(command)
            ))

    return environment, jobs


def read_crontab_file(path):
    path = Path(path)
    with open(path, "rt") as file:
        return parse_crontab(path.name, file)


