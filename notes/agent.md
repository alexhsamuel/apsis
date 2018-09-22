# Names

- chaperone
- honcho
- corra


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
  
