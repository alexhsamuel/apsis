import logging
from   ora import Time
import requests
from   urllib.parse import urlunparse

import apsis.service

#-------------------------------------------------------------------------------

class Client:

    def __init__(self, host, port=apsis.service.DEFAULT_PORT):
        self.__host = host
        self.__port = port


    def __url(self, *path):
        # FIXME
        return urlunparse((
            "http",
            f"{self.__host}:{self.__port}",
            "/api/v1/" + "/".join(path),
            "",
            "",
            "",
        ))
            

    def __get(self, *path):
        url = self.__url(*path)
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


    def get_runs(self):
        return self.__get("runs")["runs"]


    def get_run(self, run_id):
        return self.__get("runs", run_id)["runs"][run_id]


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
        


