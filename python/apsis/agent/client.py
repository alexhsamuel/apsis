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

class NoAgentError(RuntimeError):
    """
    The agent is not running.
    """

    def __init__(self, host, user):
        super().__init__(f"no agent: {user} @ {host}")



class NoSuchProcessError(LookupError):
    """
    No process with the given proc_id.
    """

    def __init__(self, proc_id):
        super().__init__(f"no such process: {proc_id}")



#-------------------------------------------------------------------------------

def get_agent_argv(*, host=None, user=None):
    """
    Returns the argument vector to start the agent on `host` as `user`.
    """
    argv = [sys.executable, "-m", "apsis.agent.main"]

    if host is not None:
        command = " ".join(argv)
        try:
            pythonpath = os.environ.get("PYTHONPATH", "")
            command = f"/usr/bin/env PYTHONPATH={pythonpath} {command}"
        except KeyError:
            pass
        argv = [
            "/usr/bin/ssh", "-q", host, 
            "exec", "/bin/bash", "-lc", 
            shlex.quote(command),
        ]

    return argv


async def start_agent(*, host=None, user=None):
    """
    Starts the agent on `hsot` as `user`.
    """
    log.info(f"starting agent on {host}")
    argv = get_agent_argv(host=host, user=user)
    proc = await asyncio.create_subprocess_exec(*argv)
    await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("agent start failed")


#-------------------------------------------------------------------------------

class Agent:

    # Number of attempts to start the agent, if a request fails.
    START_TRIES = 3

    # Delay after starting the agent before a request is sent.
    START_DELAY = 0.25

    def __init__(self, host=None, user=None, port=DEFAULT_PORT, start=True):
        """
        :param host:
          Host to run on, or `None` for local.
        :param start:
          If true, the client will attempt to start an agent automatically
          whenever the agent cannot be reached.
        """
        self.__host = host
        self.__user = user
        self.__port = port
        self.__start = bool(start)

        url_host = if_none(host, "localhost")
        self.url = f"http://{url_host}:{port}/api/v1"


    async def start(self):
        """
        Attempts to start the agent.
        """
        await start_agent(host=self.__host)


    async def request(self, method, endpoint, data=None, start=False):
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
                if not (start and self.__start):
                    raise NoAgentError(self.__host, self.__user)
                elif i == self.START_TRIES:
                    raise RuntimeError(f"failed to start agent in {i} tries")
                else:
                    await self.start()
                    await asyncio.sleep(self.START_DELAY)
            else:
                break

        log.debug(f"{method} {url} → {rsp.status_code}")
        return rsp


    async def is_running(self):
        try:
            rsp = await self.request("GET", "/running")
        except NoAgentError:
            return False
        else:
            rsp.raise_for_status()
            return True


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
            },
            start=True,
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



