# Developing

To initialize an instance DB,
```
$ apsisctl create apsis.db
```

Create a config file, for example:
```yaml
# Path to the state database.
database: apsis.db

# Path to the jobs directory.
job_dirs: jobs

# Lookback in secs for old runs.
# Currently, applied when loading runs from database at startup.
runs_lookback: 2592000  # 30 days

# Refuse to schedule runs older than this.
schedule_max_age: 86400  # 1 day
```

To run the back end,
```
$ apsisctl serve -c config.yaml
```


### Web UI

This repo contains a copy of the prod front end, which you can use if
you are not developing the front end itself.

The Vue front end was set up with the [webpack vuejs
template](https://vuejs-templates.github.io/webpack/) (an older version).

#### Developing

To run the front end in dev mode,
```
$ cd vue
$ npm install
$ npm run dev
```

#### Packaging

To produce a prod front end, 
```
$ cd vue
$ npm run build
```
then
```
$ git add --all .
$ git commit -m "Rebuild front end."
```

The Python back end service will serve the prod front end.

