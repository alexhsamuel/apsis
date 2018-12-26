# Config

```yaml
action:
- type: successor
  state: success
  job_id: close day
  args:
  - strat: "{{ strat }}"  # implied?
  - date: "{{ date + cal(strat).DAY }}"
```


### Successors

```yaml
successor:
- job_id: close day
  args:
  - strat: "{{ strat }}"  # implied?
  - date: "{{ date + cal(strat).DAY }}"
```
