# Use cases

### Web scraping jobs

### data validation jobs




# Components

### Scheduling

- update calendar support for ora
- ora named calendar repo


### Running

- live notification from agent instead of polling
- restore running jobs and other state from DB on restart
- change output to a dict
- abort running run


### Retries

```js
"retry": {
  "count": None,
  "delay": 600,
  "max_delay": 86400
}
```


### Web UI

- show parameters in run list
- run filtering by job name
- run filtering by status
- run filtering by time
- job filtering by name

- group reruns together

- a proper Vue setup with npm and or similar
- choose a javascript timestamp library


### CLUI


### Remote jobs

- remote agent


### Tests

- create a large job sample
- run an instance with high job rate to test DB throughput


### Refactor

- enapsulate job repo
- shut down scheduler loop cleanly


### Documentation


### FIXMEs


### Bugs

- fix logo on Firefox
- fix "start" etc UI buttons


