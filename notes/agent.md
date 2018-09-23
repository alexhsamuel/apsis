# Names

- agent
- chaperone
- honcho
- corra


# Strategies

1. Direct run

    The scheduler invokes each program directly, as a subprocess, under ssh for
    remote programs.
    
    - ✗ Reconnectable.
    - ✓ No external setup per host.
    - ✓ No remote code.
    - ✓ Async program updates.
    - ✗ No ssh required.
    - ✓ No orphan processes.  [if ssh configured correctly]

    Additional:
    - If ssh connection fails, connection to program is lost.  Program may
      or may not be killed.


1. Ephemeral agent, single program

    The scheduler runs an agent on the remote host to manage a single program.
    It starts the agent via an ssh invocation.  The scheduler serves HTTPS and
    the scheduler connects to it to retrieve status.  The agent lives until the
    program terminates, and the scheduler retrieves the outcome and cleans it
    up.
    
    - ✓ Reconnectable.
    - ✓ No external setup per host.
    - ✗ No remote code.
    - ✗ Async program updates.
    - ✗ No ssh required.
    - ✗ No orphan processes.  [but agent may time out]
    - ✗ Valid TLS cert.

    Additional:
    - Requires more resources per program.


1. Ephemeral agent, shared

    The scheduler starts an agent on a remote host, then connects to the agent
    to start a program.  If an existing agent is already running, it is used;
    the agent may manage multiple programs.  The agent shuts down when all
    programs have finished and the scheduler has retrieved their outcomes and
    cleaned them up.

    - ✓ Reconnectable.
    - ✓ No external setup per host.
    - ✗ No remote code.
    - ✗ Async program updates.
    - ✗ No ssh required.
    - ✗ No orphan processes.  [but agent may time out]
    - ✗ Valid TLS cert.

    Additional:
    - Agent lifecycle is complex.


1. Ephemeral agent with callback

    The scheduler runs an agent on the remote host to manage a single program.
    It starts the agent via an ssh invocation.  The scheduler serves HTTP and
    the agent connects back with status updates.  When the program completes,
    the agent sends the outcome to the scheduler and shuts down.

    - ✓ Reconnectable.  [automatic!]
    - ✓ No external setup per host.
    - ✗ No remote code.
    - ✓ Async program updates.
    - ✗ No ssh required.
    - ✗ No orphan processes.  [but agent may time out]
    - ✓ Valid TLS cert.
    
    Additional:
    - Hosts must be able to connect back to agent.
    - Poor visibility.  If agent malfunctions or can't connect back, no one
      knows.  Scheduler cannot request status from agent.


1. Long-running agent

    An agent runs on each host, managed by an external system such as init or
    supervisor.  The agent runs all jobs on that host, as all uses.  The
    agent serves requests from the scheduler via JSON over HTTPS.
    
    - ✓ Reconnectable.
    - ✗ No external setup per host.
    - ✗ No remote code.
    - ✗ Async program updates. 
    - ✓ No ssh required.
    - ✓ No orphan processes.
    - ✓ Valid TLS cert.

    Additional:

    - Good visibility to examine what's going on outside scheduler.  Central
      logging and API.
    - Requires additional monitoring of agent health.
    

# Local chaperone

- Can write outputs to spool files and then exit.
- But needs to hold an ssh connection open for the life of the remote process.
- We can "reconnect" by watching for outputs in spool files.
  - Note that this is not async, unless we use inotify.
- All sudo + ssh is orthogonal.

API:

```py
def build_program(argv, options={}):
    """
    Constructs a shell command to run `argv`.
    """
    command = "exec " + " ".join( shlex.quote(a) for a in argv )
    return build_command(command, host=host, user=user, options=options)


def build_command(command, host=None, user=None, options={}):
    """
    Constructs an argv to run shell `command` as `user` on `host`.

    `options` may include,
    - `host`
    - `port`
    - mode (ssh-as, sudo-then-ssh, ssh-then-sudo, etc.)
    - ssh options
    """

```



# Remote-style agent

```
agent.py < program.json
```


program.json:
```js
{
  program: {
    argv: [
      '/path/to/executable',
      'arg1',
      'arg2'
    ],
    cwd: '/path/to/dir',
    env: {
      'VAR1': 'value1',
      'VAR2': 'value2'
    },
    stdin: null
  },
  callback: {
    url: 'https://agenthost:8050/api/v1/agent/PROG-ID',
    method: 'GET',
    token: 'kHJBeIu1r0Xhb9y0FGeDU-sVPPfmoqaMlNSAw0L9ipU'
  },
  config: {
    retry_frequency: 10,
    timeout: 86400,
    output_buffer: 65536,
    output_latency: 1,
  }
}
```

prints:
```js
{
  proc_id: 'PROC-ID', ??
  state: 'running',
  program: {
    ...
  },
  agent_pid: 12344,
  pid: 12345,
  exection: null,
  status: null,
  return_code: null,
  signal: null,
  rusage: null,
  start_time: '2018-09-14T22:31:24+00:00',
  end_time: null,
}
```

callbacks:

- `/api/v1/agent/PROG-ID/output/NAME`: append output
- `/api/v1/agent/PROG-ID/completed`: completed

signals:

- SIGTERM: send SIGTERM to program


# Questions

- How does progressive output work in the Apsis server?
  - When is new output_id attached to run?
  - How is incremental data stored?
  
