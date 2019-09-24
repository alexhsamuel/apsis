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
from   apsis.lib.sys import get_username
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
            f"agent start failed with returncode={returncode}: {err}")



#-------------------------------------------------------------------------------

# FIXME-CONFIG: Configure how we become other users and log in to other hosts.

SSH_OPTIONS = dict(
    BatchMode               ="yes",
    CheckHostIP             ="no",  # FIXME-CONFIG
    ClearAllForwardings     ="yes",
    ForwardAgent            ="no",
    ForwardX11              ="no",
    StrictHostKeyChecking   ="no",  # FIXME-CONFIG
)

def _get_agent_argv(*, host=None, user=None, connect=None):
    """
    Returns the argument vector to start the agent on `host` as `user`.
    """
    # FIXME-CONFIG: Configure how to start remote agents.
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


async def start_agent(*, host=None, user=None, connect=None, timeout=10):
    """
    Starts the agent on `host` as `user`.

    :param connect:
      If true, connect to a running instance only.  If false, fail if an 
      instance is already running.  If None, either start or connect.
    :param timeout:
      Timeout in sec.
    :return:
      The agent port and token.
    """
    log.info(f"starting agent on {host}")
    argv = _get_agent_argv(host=host, user=user, connect=connect)
    log.info(" ".join(argv))
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        raise AgentStartError(-1, "timeout")

    # Show the agent's log output.
    for line in err.decode().splitlines():
        log.debug("agent log: " + line)

    if proc.returncode == 0:
        # The agent is running.  Whether it just started or not, it prints
        # out its port and secret token.
        try:
            data, = out.decode().splitlines()
            port, token = data.split()
            return int(port), token
        except (TypeError, ValueError):
            raise AgentStartError(proc.returncode, out.decode())

    else:
        raise AgentStartError(proc.returncode, err.decode())


#-------------------------------------------------------------------------------

class Agent:

    # Delays between attempts to start the agent-- back off.  The number of
    # attempts is the number of delays.
    START_DELAYS = [ 0.5 * i**2 for i in range(6) ]

    def __init__(self, host=None, user=None, *, connect=None):
        """
        :param host:
          Host to run on, or none for local.
        :param user:
          User to run as, or none for the current user.
        :param connect:
          If true, connect to a running instance only.  If false, fail if an 
          instance is already running.
        """
        self.__host     = host
        self.__user     = user
        self.__connect  = connect

        self.__lock     = asyncio.Lock()
        self.__conn     = None


    def __str__(self):
        return f"agent {self.__user}@{self.__host} on port {self.__port}"


    async def connect(self, *, reconnect=False):
        """
        Attempts to start or connect to the agent.

        :return:
          The agent port and token.
        """
        async with self.__lock:
            if reconnect or self.__conn is None:
                self.__conn = await start_agent(
                    host    =self.__host,
                    user    =self.__user,
                    connect =self.__connect,
                )
                log.info(
                    f"agent host={self.__host} user={self.__user} connected: "
                    f"port={self.__conn[0]}")

            return self.__conn


    async def request(self, method, endpoint, data=None, *, restart=False):
        """
        Performs an HTTP request to the agent.

        :param method:
          HTTP method.
        :param endpoint:
          API endpoint path fragment.
        :param data:
          Payload data, to send as JSON.
        :param restart:
          If true, the client will attempt to start an agent automatically
          if the agent conenction fails.
        :return:
          The response.
        """
        # FIXME: Use async requests.

        # Delays in sec before each attempt to connect.
        delays = self.START_DELAYS if restart else [0]

        for delay in delays:
            if delay > 0:
                await asyncio.sleep(delay)

            port, token = await self.connect()
            url_host = if_none(self.__host, "localhost")
            url = f"https://{url_host}:{port}/api/v1" + endpoint

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
                    rsp = requests.request(
                        method, url,
                        json=data,
                        verify=False,
                        headers={
                            "X-Auth-Token": token,
                        }
                    )

            except requests.ConnectionError:
                # Try again.
                log.debug(f"{method} {url} → connection error")
                # FIXME: Do this properly.
                async with self.__lock:
                    self.__conn = None
                continue

            else:
                log.debug(f"{method} {url} → {rsp.status_code}")

                if rsp.status_code == 403:
                    # Forbidden.  A different agent is running on that port.  We
                    # should start our own.
                    log.info("wrong agent; reconnecting")

                    # FIXME: Do this properly.
                    async with self.__lock:
                        self.__conn = None
                    continue

                else:
                    # Request submitted successfully.
                    return rsp

        else:
            # Ran out of connection attempts.
            raise NoAgentError(self.__host, self.__user)


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


    async def start_process(
            self, argv, cwd="/", env=None, stdin=None, restart=False):
        """
        Starts a process.

        :return:
          The new process, which will either be in state "run" or "err".
        """
        username = get_username() if self.__user is None else self.__user
        rsp = await self.request(
            "POST", "/processes", data={
                "program": {
                    "username"  : username,
                    "argv"      : [ str(a) for a in argv ],
                    "cwd"       : str(cwd),
                    "env"       : env,
                    "stdin"     : stdin,
                },
            },
            restart=restart
        )
        rsp.raise_for_status()
        return rsp.json()["process"]


    async def get_process(self, proc_id, *, restart=False):
        """
        Returns inuformation about a process.
        """
        rsp = await self.request(
            "GET", f"/processes/{proc_id}", restart=restart)
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



