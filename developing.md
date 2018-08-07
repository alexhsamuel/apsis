# Developing

To run the back end,
```
$ python -m apsis.service.main jobs
```

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
and commit the results.  The Python back end service will serve the prod front
end.

