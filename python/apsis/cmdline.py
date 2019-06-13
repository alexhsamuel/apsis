import fixfmt.table
from   ora import Time, Daytime, now, get_display_time_zone

import apsis.lib.itr
from   apsis.lib.terminal import COLOR, BLK, WHT, RED, BLD, NBL

#-------------------------------------------------------------------------------

STATE_COLOR = {
    "new"       : COLOR( 17),
    "scheduled" : COLOR(243),
    "waiting"   : COLOR(241),
    "running"   : COLOR(136),
    "success"   : COLOR( 29),
    "failure"   : COLOR(124),
    "error"     : COLOR(127),
}

STATE_SYMBOL = {
    "new"       : ".",
    "scheduled" : "O",
    "waiting"   : "|",
    "running"   : ">",
    "success"   : "+",
    "failure"   : "X",
    "error"     : "!",
}

RUN = COLOR( 36)
JOB = COLOR( 30)
ARG = COLOR( 60)

#-------------------------------------------------------------------------------

def print_lines(lines):
    for line in lines:
        print(line)


def prefix(prefix, lines):
    for line in lines:
        yield prefix + line


def format_jso(jso, indent=0):
    ind = " " * indent
    wid = 12 - indent
    for key, value in jso.items():
        yield f"{ind}{key:{wid}s}: {value}"


def format_state_symbol(state):
    return STATE_COLOR[state] + STATE_SYMBOL[state] + BLK

format_state_symbol.width = 1


def format_program(program, indent=0):
    yield from format_jso(program, indent=indent)


def format_schedule(schedule, indent=0):
    yield from format_jso(schedule, indent=indent)


def format_instance(run):
    return (
        f"{JOB}{run['job_id']}{BLK} "
        + " ".join( f"{k}={ARG}{v}{BLK}" for k, v in run["args"].items() )
    )


def format_job(job):
    # fmt = lambda k, v: f"{k:12s}: {v}"
    # yield fmt("job_id", job["job_id"])
    # yield fmt("url", job["url"])
    # yield fmt("params", ", ".join(job["params"]))
    # yield "program"
    # yield from format_program(job["program"], indent=2)
    # yield "schedules"
    # for schedule in job["schedules"]:
    #     yield from format_schedule(schedule, indent=2)
    yield from _fmt(None, job)


def format_jobs(jobs):
    table = fixfmt.table.RowTable()
    table.extend(
        {
            "job_id": job["job_id"],
            "params": ", ".join(job["params"]),
        }
        for job in jobs
    )
    yield from table


def _fmt(name, val, width=16, indent=-2):
    prefix = " " * indent
    if isinstance(val, dict):
        if name is not None:
            yield prefix + name + ":"
        for name, val in val.items():
            yield from _fmt(name, val, width, indent + 2)
    elif isinstance(val, list):
        if name is not None:
            yield prefix + name + ":"
        for val in val:
            yield from _fmt("-", val, width, indent + 2)
    else:
        if name is None:
            name = ""
        yield prefix + fixfmt.pad(name, width - indent) + ": " + str(val)


def format_run(run):
    b = "✦"

    # Run ID.
    run_id = run["run_id"]
    yield f"{BLD}run {RUN}{run_id}{BLK}{NBL}"

    # The job.
    job = format_instance(run)
    yield f"{b} job {job}"

    # Rerun info.
    if run["rerun"] != run_id:
        yield f"{b} rerun of run {RUN}{run['rerun']}{BLK}"

    # Current state and relevant time.
    time = lambda n: format_time(run["times"].get(n, ""))
    state = run["state"]
    if state == "scheduled":
        time = "for " + time("schedule")
    elif state == "running":
        time = "since " + time("running")
    else:
        time = "at " + time(state)
    elapsed = run["meta"].get("elapsed")
    if elapsed is not None:
        time += " elapsed " + format_elapsed(elapsed).lstrip()
    yield f"{STATE_COLOR[state]}{STATE_SYMBOL[state]} {state}{BLK} {time}"

    # Message, if any.
    if run["message"] is not None:
        yield f"➔ {WHT}{run['message']}{BLK}"
    
    yield ""


def format_run_history(run_history):
    table = fixfmt.table.RowTable()
    table.extend(
        {
            "timestamp": Time(h["timestamp"]),
            "message": h["message"],
        }
        for h in run_history
    )
    table.fmts["timestamp"] = format_time
    return table


RUNS_CFG = fixfmt.table.update_cfg(fixfmt.table.RowTable.DEFAULT_CFG, {
    "header": {
        "separator": {
            "between": " ",
        },
    },
    "underline": {
        "separator": {
            "between": " ",
        },
    },
    "row": {
        "separator": {
            "between": " ",
        },
    },
})

def format_runs(runs, *, reruns=False):
    # FIXME: Does this really make sense?
    def start_time(run):
        return run["times"].get("running", run["times"].get("schedule", ""))

    # FIXME: Support other sorts.
    runs = sorted(runs.values(), key=start_time)
    if reruns:
        runs = sorted(runs, key=lambda r: r["rerun"])

    cur = now()
    def elapsed(run):
        try:
            start = Time(run["times"]["running"])
        except KeyError:
            return None
        state = run["state"]
        if state == "running":
            return cur - start
        elif state in {"success", "failure", "error"}:
            stop = Time(run["times"][state])
            return stop - start
        else:
            return None

    table = fixfmt.table.RowTable(RUNS_CFG)
    for pos, run in apsis.lib.itr.find_groups(runs, group=lambda r: r["rerun"]):
        row = {
            "run_id"    : RUN + run["run_id"] + BLK,
            "S"         : run["state"],
            "start"     : start_time(run),
            "elapsed"   : elapsed(run),
            "job_id"    : JOB + run["job_id"] + BLK,
            "args"      : " ".join( f"{k}={v}" for k, v in run["args"].items() ),
          # **run["args"],
        }
        table.append(**row)
        if reruns and pos in "lo":
            table.text("")

    if table.num_rows > 0:
        table.fmts["S"] = format_state_symbol
        table.fmts["start"] = format_time
        table.fmts["elapsed"] = format_elapsed
        yield from table

    else:
        yield f"{RED}No runs.{BLK}"

    if not reruns:
        yield ""


def format_elapsed(secs):
    secs = round(secs)
    m, s = divmod(secs, 60)
    if m < 60:
        return f"   {m:2d}:{s:02d}"
    else:
        h, m = divmod(m, 60)
        return f"{h:2d}:{m:02d}:{s:02d}"
    # FIXME: Add formats for longer times.

format_elapsed.width = 8


#-------------------------------------------------------------------------------

def parse_at_time(string):
    """
    Parses a time for when to run.

    Accepts a full time or a daytime (next occurrence).
    """
    if string == "now":
        return "now"

    try:
        return Time(string)
    except ValueError:
        pass

    try:
        daytime = Daytime(string)
    except ValueError:
        pass
    else:
        # Assume this is today's daytime in the display time zone, unless
        # that has already passed, in which case use tomorrow.
        z = get_display_time_zone()
        date, daytime_now = now() @ z
        return (date if daytime_now < daytime else date + 1, daytime) @ z

    # FIXME: Accept expressions like "1 hour".

    raise ValueError(f"cannot interpret as time: {string}")


def format_time(time):
    return "" if time is "" else format(Time(time), "%D %C@")

format_time.width = 19


