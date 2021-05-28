# Architecure

### Runs

The existing `RunStore` should be refactored first.

First factor out run ID allocation.



# Old

```
apsis.runs:{run_id} = hash
apsis.runs:{run_id}:json = string (JSON)

state:scheduled = set
state:running = set
state:completed = set
```
