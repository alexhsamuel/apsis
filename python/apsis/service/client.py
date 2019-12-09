import logging
from   ora import Time
import os
from   collections import namedtuple
import requests
from   urllib.parse import quote, urlunparse

import apsis.service

#-------------------------------------------------------------------------------

Address = namedtuple("Address", ("host", "port"))

def get_address() -> Address:
    """
    Returns the configured host and port where Apsis runs.
    """
    try:
        loc = os.environ["APSIS_HOST"]
    except KeyError:
        host, port = "localhost", apsis.service.DEFAULT_PORT
    else:
        try:
            host, port = loc.split(":", 1)
            port = int(port)
        except ValueError:
            host, port = loc, apsis.service.DEFAULT_PORT
        else:
            port = int(port)
    return Address(host, port)



class APIError(RuntimeError):

    def __init__(self, status, error, jso):
        super().__init__(error)
        self.status = status
        self.jso = jso



NO_ARG = object()

class Client:

    def __init__(self, address=None):
        """
        :param addr:
          Apsis hostname and port, or none for default.
        """
        self.__addr = get_address() if address is None else Address(*address)


    def __url(self, *path, **query):
        query = "&".join(
            str(k) if v is NO_ARG else f"{k}={quote(str(v))}"
            for k, v in query.items()
            if v is not None
        )
        return urlunparse((
            "http",
            f"{self.__addr.host}:{self.__addr.port}",
            "/".join(path),
            "",
            query,
            "",
        ))


    def __request(self, method, *path, data=None, **query):
        url = self.__url(*path, **query)
        logging.debug(f"{method} {url} data={data}")
        resp = requests.request(method, url, json=data)
        if 200 <= resp.status_code < 300:
            return resp.json()
        else:
            try:
                jso = resp.json()
                error = jso.get("error", "unknown error")
            except Exception:
                jso = {}
                error = "unknown error"
            raise APIError(resp.status_code, error, jso)


    def __get(self, *path, **query):
        return self.__request("GET", *path, **query)


    def __post(self, *path, data, **query):
        return self.__request("POST", *path, data=data, **query)


    def __put(self, *path, data=None, **query):
        return self.__request("PUT", *path, data=data, **query)


    def get_history(self, run_id):
        return self.__get("/api/v1/runs", run_id, "history")["run_history"]


    def get_job(self, job_id):
        return self.__get("/api/v1/jobs", job_id)


    def get_job_runs(self, job_id):
        return self.__get("/api/v1/jobs", job_id, "runs")["runs"]


    def get_jobs(self):
        return self.__get("/api/v1/jobs")


    def get_output(self, run_id, output_id) -> bytes:
        url = self.__url("/api/v1/runs", run_id, "output", output_id)
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content


    def signal(self, run_id, signal):
        """
        Sends `signal` to a running processes.
        """
        return self.__put("/api/v1/runs", run_id, "signal", str(signal))


    def get_runs(self, *, job_id=None, state=None, reruns=False,
                 since=None, until=None):
        return self.__get(
            "/api/v1/runs",
            job_id  =job_id,
            state   =state,
            reruns  =reruns,
        )["runs"]


    def get_run(self, run_id):
        return self.__get("/api/v1/runs", run_id)["runs"][run_id]


    def rerun(self, run_id):
        run, = self.__post("/api/v1/runs", run_id, "rerun", data={})["runs"].values()
        return run


    def schedule(self, job_id, args, time):
        """
        Creates and schedules a new run.
        """
        job_id  = str(job_id)
        args    = { str(k): str(v) for k, v in args.items() }
        time    = "now" if time == "now" else str(Time(time))

        data = {
            "job_id": job_id,
            "args": args,
            "times": {
                "schedule": time,
            }
        }
        runs = self.__post("/api/v1/runs", data=data)["runs"]
        return next(iter(runs.values()))


    def __schedule(self, time, job):
        time = "now" if time == "now" else str(Time(time))
        data = {
            "job": job,
            "times": {
                "schedule": time,
            },
        }
        runs = self.__post("/api/v1/runs", data=data)["runs"]
        return next(iter(runs.values()))


    def schedule_program(self, time, args):
        """
        :param time:
          The schedule time, or "now" for immediate.
        :param args:
          The argument vector.  The first item is the path to the program
          to run.
        """
        args = [ str(a) for a in args ]
        return self.__schedule(time, {"program": args})


    def schedule_shell_program(self, time, command):
        """
        :param time:
          The schedule time, or "now" for immediate.
        :param command:
          The shell command to run.
        """
        return self.__schedule(time, {"program": str(command)})
        

    def reload_jobs(self, *, dry_run=False):
        return self.__post("/api/control/reload_jobs", data={}, dry_run=dry_run)


    def shut_down(self, restart=False):
        query = {"restart": NO_ARG} if restart else {}
        self.__post("/api/control/shut_down", data={}, **query)



