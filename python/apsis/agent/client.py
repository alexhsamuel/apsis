import asyncio
import logging
import requests
import subprocess
import sys

from   . import DEFAULT_PORT

log = logging.getLogger("agent.client")

#-------------------------------------------------------------------------------

class Agent:

    # Number of attempts to start the agent, if a request fails.
    START_TRIES = 3

    # Delay after starting the agent before a request is sent.
    START_DELAY = 0.25

    def __init__(self, host="localhost", port=DEFAULT_PORT):
        self.url = f"http://{host}:{port}/api/v1"


    async def start(self):
        """
        Attempts to start the agent.
        """
        # FIXME: Start async.
        log.info("starting agent")
        subprocess.run([sys.executable, "-m", "apsis.agent.main"])


    async def request(self, method, endpoint, data=None):
        """
        Performs an HTTP request to the agent.

        :param method:
          HTTP method.
        :param endpoint:
          API endpoint path fragment.
        :param data:
          Payload data, to send as JSON.
        """
        url = self.url + endpoint
        log.debug(f"{method} {url}")
        
        # FIXME: Use async requests.

        for i in range(self.START_TRIES + 1):
            try:
                rsp = requests.request(method, url, json=data)
            except requests.ConnectionError:
                if i == self.START_TRIES:
                    break
                else:
                    await self.start()
                    await asyncio.sleep(self.START_DELAY)

        log.debug(f"{method} {url} -> {rsp.status_code}")
        rsp.raise_for_status()
        return rsp.json()


    async def get_processes(self):
        return (await self.request("GET", "/processes"))["processes"]


    async def start_process(self, argv, cwd="/", env=None, stdin=None):
        return (await self.request(
            "POST", "/processes", data={
                "argv"  : [ str(a) for a in argv ],
                "cwd"   : str(argv),
                "env"   : env,
                "stdin" : stdin,
            })
        )["process"]


    async def get_process(self, proc_id):
        return (await self.request("GET", f"/processes/{proc_id}"))["process"]


    async def del_process(self, proc_id):
        return (await self.request("DELETE", f"/processes/{proc_id}"))["shutdown"]



