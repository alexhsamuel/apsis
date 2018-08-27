import asyncio
import logging
import os
import requests
import shlex
import sys

from   . import DEFAULT_PORT
from   apsis.lib.py import if_none

log = logging.getLogger("agent.client")

#-------------------------------------------------------------------------------

class NoSuchProcessError(LookupError):

    def __init__(self, proc_id):
        super().__init__(f"no such process: {proc_id}")



#-------------------------------------------------------------------------------

class Agent:

    # Number of attempts to start the agent, if a request fails.
    START_TRIES = 3

    # Delay after starting the agent before a request is sent.
    START_DELAY = 0.25

    # FIXME: This is not the best.
    REMOTE_AGENT = f"env PYTHONPATH={os.environ.get('PYTHONPATH', '')} {sys.executable} -m apsis.agent.main"

    def __init__(self, host=None, port=DEFAULT_PORT, start=True):
        """
        :param host:
          Host to run on, or `None` for local.
        :param start:
          If true, the client will attempt to start an agent automatically
          whenever the agent cannot be reached.
        """
        self.__host = host
        self.__port = port
        self.__start = bool(start)

        url_host = if_none(host, "localhost")
        self.url = f"http://{url_host}:{port}/api/v1"


    async def start(self):
        """
        Attempts to start the agent.
        """
        log.info(f"starting agent on {self.__host}")

        if self.__host is None:
            argv = [sys.executable, "-m", "apsis.agent.main"]
        else:
            argv = [
                "/usr/bin/ssh", "-q", self.__host, 
                "/bin/bash", "-lc", 
                shlex.quote(self.REMOTE_AGENT),
            ]

        proc = await asyncio.create_subprocess_exec(*argv)
        await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("agent start failed")


    async def request(self, method, endpoint, data=None):
        """
        Performs an HTTP request to the agent.

        :param method:
          HTTP method.
        :param endpoint:
          API endpoint path fragment.
        :param data:
          Payload data, to send as JSON.
        :return:
          The response, if the status code is 2xx or 4xx.
        """
        url = self.url + endpoint
        log.debug(f"{method} {url}")
        
        # FIXME: Use async requests.

        for i in range(self.START_TRIES + 1):
            try:
                rsp = requests.request(method, url, json=data)
            except requests.ConnectionError:
                if not self.__start:
                    raise RuntimeError("no agent")
                elif i == self.START_TRIES:
                    raise RuntimeError(f"failed to start agent in {i} tries")
                else:
                    await self.start()
                    await asyncio.sleep(self.START_DELAY)
            else:
                break

        log.debug(f"{method} {url} -> {rsp.status_code}")
        if 200 <= rsp.status_code < 300 or 400 <= rsp.status_code < 500:
            return rsp
        else:
            rsp.raise_for_status()


    async def get_processes(self):
        rsp = await self.request("GET", "/processes")
        rsp.raise_for_status()
        return rsp.json()["processes"]


    async def start_process(self, argv, cwd="/", env=None, stdin=None):
        """
        Starts a process.

        :return:
          The new process, which will either be in state "rub" or "err".
        """
        rsp = await self.request(
            "POST", "/processes", data={
                "program": {
                    "argv"  : [ str(a) for a in argv ],
                    "cwd"   : str(cwd),
                    "env"   : env,
                    "stdin" : stdin,
                },
            }
        )
        rsp.raise_for_status()
        return rsp.json()["process"]


    async def get_process(self, proc_id):
        """
        Returns inuformation about a process.
        """
        rsp = await self.request("GET", f"/processes/{proc_id}")
        if rsp.status_code == 404:
            raise NoSuchProcessError(proc_id)
        rsp.raise_for_status()
        return rsp.json()["process"]


    async def get_process_output(self, proc_id) -> bytes:
        """
        Returns process output.
        """
        rsp = await self.request("GET", f"/processes/{proc_id}/output")
        if rsp.status_code == 404:
            raise NoSuchProcessError(proc_id)
        rsp.raise_for_status()
        return rsp.content


    async def del_process(self, proc_id):
        """
        Deltes a process.  The process may not be running.
        """
        rsp = await self.request("DELETE", f"/processes/{proc_id}")
        if rsp.status_code == 404:
            raise NoSuchProcessError(proc_id)
        rsp.raise_for_status()
        return rsp.json()["shutdown"]


    async def shut_down(self):
        """
        Shuts down an agent, if there are no remaining processes.
        """
        rsp = await self.request("POST", f"/shutdown")
        rsp.raise_for_status()
        return rsp.json()["shutdown"]



