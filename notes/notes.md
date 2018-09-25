# SQLite

Performance test of appending to string fields, in `work/sqlite-concat.py`.

```py
with engine.begin() as con:
    con.execute("UPDATE data SET data = data || ?", (data, ))
```

The first 1 kB append takes 2 ms.  At 1 MB, the append takes 20 ms.  Appears to
be roughly linear.  Same for both string and binary columns.  Timed on purslane.

