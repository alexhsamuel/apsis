# Developing

To run the back end,
```
$ python -m apsis.service.main jobs
```

The Vue front end was set up with the [webpack vuejs
template](https://vuejs-templates.github.io/webpack/) (an older version).

To run the front end in dev mode,
```
$ cd vue
$ npm install
$ npm run dev
```

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

