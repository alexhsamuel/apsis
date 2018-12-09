import asyncio
import itertools
import logging
import os
import requests
import shlex
import subprocess
import sys
import warnings

from   apsis.lib.py import if_none

try:
    # Older requests vendor urllib3.
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
except ImportError:
    # Newer requests uses the proper package.
    from urllib3.exceptions import InsecureRequestWarning

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



class AgentStartError(RuntimeError):
    """
    The agent failed to start.
    """

    def __init__(self, returncode, err):
        super().__init__(
            f"agent start failed with returncode={returncode}: {err.decode()}")



#-------------------------------------------------------------------------------

# FIXME-CONFIG: Configure how we become other users and log in to other hosts.

# FIXME-CONFIG: Make configurable.
SSH_OPTIONS = dict(
    CheckHostIP="no",
    ClearAllForwardings="yes",
    ForwardAgent="no",
    ForwardX11="no",
    StrictHostKeyChecking="no",
)

def _get_agent_argv(*, host=None, user=None, connect=None):
    """
    Returns the argument vector to start the agent on `host` as `user`.
    """
    argv = [sys.executable, "-m", "apsis.agent.main"]

    try:
        pythonpath = os.environ.get("PYTHONPATH", "")
        argv = ["/usr/bin/env", "PYTHONPATH=" + pythonpath, *argv]
    except KeyError:
        pass

    if connect is True:
        argv.append("--connect")
    elif connect is False:
        argv.append("--no-connect")

    if host is not None:
        command = " ".join(argv)
        argv = [
            "/usr/bin/ssh",
            "-o", "BatchMode=yes",
            *itertools.chain.from_iterable(
                ["-o", f"{k}={v}"]
                for k, v in SSH_OPTIONS.items()
            )
        ]
        if user is not None:
            argv.extend(["-l", user])
        argv.extend([
            host, 
            "exec", "/bin/bash", "-lc", shlex.quote(command),
        ])

    elif user is not None:
        argv = ["/usr/bin/sudo", "-u", user, *argv]

    return argv


async def start_agent(*, host=None, user=None, connect=None):
    """
    Starts the agent on `host` as `user`.

    :param connect:
      If true, connect to a running instance only.  If false, fail if an 
      instance is already running.
    :return:
      The agent port and token.
    """
    log.info(f"starting agent on {host}")
    argv = _get_agent_argv(host=host, user=user, connect=connect)
    log.info(" ".join(argv))
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = await proc.communicate()

    if proc.returncode == 0:
        # The agent is running.  Whether it just started or not, it prints
        # out its port and secret token.
        data, = out.decode().splitlines()
        port, token = data.split()
        return int(port), token

    else:
        raise AgentStartError(proc.returncode, err)


#-------------------------------------------------------------------------------

class Agent:

    # Number of attempts to start the agent, if a request fails.
    START_TRIES = 3

    # Delay after starting the agent before a request is sent.
    START_DELAY = 0.25

    def __init__(self, host=None, user=None, *, connect=None, restart=False):
        """
        :param host:
          Host to run on, or `None` for local.
        :param connect:
          If true, connect to a running instance only.  If false, fail if an 
          instance is already running.
        :param restart:
          If true, the client will attempt to start an agent automatically
          whenever the agent cannot be reached.
        """
        self.__host     = host
        self.__user     = user
        self.__connect  = connect
        self.__restart  = bool(restart)

        self.__port     = None
        self.__token    = None


    def __str__(self):
        return f"agent {self.__user}@{self.__host} on port {self.__port}"


    async def start(self):
        """
        Attempts to start the agent.
        """
        self.__port, self.__token = await start_agent(
            host=self.__host, user=self.__user, connect=self.__connect)

        log.info(f"agent started: port={self.__port}")
        return self


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
          The response.
        """
        if self.__port is None or self.__token is None:
            if self.__restart:
                await self.start()
            else:
                raise NoAgentError(self.__host, self.__user)

        url_host = if_none(self.__host, "localhost")
        url = f"https://{url_host}:{self.__port}/api/v1" + endpoint
        log.debug(f"{method} {url}")

        # FIXME: Use async requests.

        for i in range(self.START_TRIES + 1):
            try:
                # FIXME: For now, we use no server verification when
                # establishing the TLS connection to the agent.  The agent uses
                # a generic SSL cert with no real host name, so host
                # verification cannot work; we'd have to generate a certificate
                # for each agent host.  For now at least we have connection
                # encryption.
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", category=InsecureRequestWarning)
                    rsp = requests.request(method, url, json=data, verify=False)

            except requests.ConnectionError:
                if self.__restart:
                    if i == self.START_TRIES:
                        raise RuntimeError(
                            f"failed to start agent in {i} tries")
                    else:
                        await self.start()
                        await asyncio.sleep(self.START_DELAY)
                else:
                    raise
            else:
                # Request submitted successfully.
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
        return rsp.json()["stop"]


    async def stop(self):
        """
        Shuts down an agent, if there are no remaining processes.
        """
        rsp = await self.request("POST", f"/stop")
        rsp.raise_for_status()
        return rsp.json()["stop"]



