import asyncio
import logging
import requests
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
        log.info("starting agent")
        argv = [sys.executable, "-m", "apsis.agent.main"]
        proc = await asyncio.create_subprocess_exec(*argv)
        await proc.communicate()
        # if proc.returncode != 0:
        #     raise RuntimeError("agent start failed")


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
            else:
                break

        log.debug(f"{method} {url} -> {rsp.status_code}")
        if 400 <= rsp.status_code < 500:
            raise RuntimeError(rsp.json()["error"])
        else:
            rsp.raise_for_status()

        return rsp


    async def get_processes(self):
        return (await self.request("GET", "/processes")).json()["processes"]


    async def start_process(self, argv, cwd="/", env=None, stdin=None):
        """
        Starts a process.

        :return:
          The new process, which will either be in state "rub" or "err".
        """
        return (await self.request(
            "POST", "/processes", data={
                "program": {
                    "argv"  : [ str(a) for a in argv ],
                    "cwd"   : str(cwd),
                    "env"   : env,
                    "stdin" : stdin,
                },
            })
        ).json()["process"]


    async def get_process(self, proc_id):
        """
        Returns inuformation about a process.
        """
        return (
            await self.request("GET", f"/processes/{proc_id}")
        ).json()["process"]


    async def get_process_output(self, proc_id):
        """
        Returns process output.
        """
        return (
            await self.request("GET", f"/processes/{proc_id}/output")
        ).content


    async def del_process(self, proc_id):
        """
        Deltes a process.  The process may not be running.
        """
        return (
            await self.request("DELETE", f"/processes/{proc_id}")
        ).json()["shutdown"]


    async def shut_down(self):
        """
        Shuts down an agent, if there are no remaining processes.
        """
        return (
            await self.request("POST", f"/shutdown")
        ).json()["shutdown"]



