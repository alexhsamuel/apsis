
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
  
