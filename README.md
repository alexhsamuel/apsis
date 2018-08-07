Apsis is a task scheduler.  Its main responsibility is to run tasks at specific
times, including recurring tasks.  It also tracks running tasks, and the state
of completed tasks.  It supports simple and complex schedules, such as once an
hour, or 4:00 PM US/Eastern on the day before every US holiday.


### Components

The components of Apsis are,

- A Python 3 async scheduling library, suitable for embedding in other
  applications that require task scheduling.

- A service that schedules tasks and exposes its state via a REST API.

- A web UI for interacting with the service.

- A command line UI for interacting with the service.


### Dependencies

Apsis is built on,
- Python 3.6
- the [Sanic](https://github.com/channelcat/sanic) web server
- the [Ora](https://github.com/alexhsamuel/ora) time library
- [Vue.js](https://vuejs.org/) for the web UI


