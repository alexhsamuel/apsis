import logging
import requests
from   urllib.parse import urlunparse

import apsis.service
import apsis.types

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def program_from_jso(jso):
    # FIXME
    return {}


def schedule_from_jso(jso):
    # FIXME
    return {}


def job_from_jso(jso):
    job = apsis.types.Job(
        jso["job_id"],
        jso["params"],
        ( schedule_from_jso(s) for s in jso["schedules"] ),
        program_from_jso(jso["program"])
    )
    job.url = jso["url"]
    return job


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


    def get_jobs(self):
        return ( job_from_jso(j) for j in self.__get("jobs") )



