import logging
from   ora import Time
import requests
from   urllib.parse import quote, urlunparse

import apsis.service

#-------------------------------------------------------------------------------

class Client:

    def __init__(self, host, port=apsis.service.DEFAULT_PORT):
        self.__host = host
        self.__port = port


    def __url(self, *path, **query):
        query = "&".join(
            f"{k}={quote(str(v))}"
            for k, v in query.items()
            if v is not None
        )
        return urlunparse((
            "http",
            f"{self.__host}:{self.__port}",
            "/api/v1/" + "/".join(path),
            "",
            query,
            "",
        ))


    def __get(self, *path, **query):
        url = self.__url(*path, **query)
        logging.debug(f"GET {url}")
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()


    def __post(self, *path, data):
        url = self.__url(*path)
        logging.debug(f"POST {url}")
        resp = requests.post(url, json=data)
        resp.raise_for_status()
        return resp.json()


    def get_job(self, job_id):
        return self.__get("jobs", job_id)


    def get_job_runs(self, job_id):
        return self.__get("jobs", job_id, "runs")["runs"]


    def get_jobs(self):
        return self.__get("jobs")


    def get_output(self, run_id) -> bytes:
        url = self.__url("runs", run_id, "output")
        logging.debug(f"GET {url}")
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.content


    def get_runs(self, *, job_id=None, state=None, reruns=False,
                 since=None, until=None):
        return self.__get(
            "runs",
            job_id  =job_id,
            state   =state,
            reruns  =reruns,
        )["runs"]


    def get_run(self, run_id):
        return self.__get("runs", run_id)["runs"][run_id]


    def rerun(self, run_id):
        run, = self.__post("runs", run_id, "rerun", data={})["runs"].values()
        return run


    def __schedule(self, time, job):
        time = "now" if time == "now" else str(Time(time))
        data = {
            "job": job,
            "times": {
                "schedule": time,
            },
        }
        runs = self.__post("runs", data=data)["runs"]
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
        


