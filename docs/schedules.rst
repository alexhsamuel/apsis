.. _schedules:

Configuring Schedules
=====================

The `schedule` key configures when Apsis should schedule runs of the job.  You
can give a single schedule, or a list of multiple schedules.

Each schedule has a `type` key, which specifies the schedule to use.  These are
described below.


Enabled
-------

Each schedule has an `enabled` key.  If set to false, the schedule is disabled
and Apsis schedules no runs with it.  If omitted, the schedule is eabnled.


Args
----

Each schedule has an `args` key, which specifies the arg values corresponding to
the job's params.  For example, when you schedul ethe job `check
host(hostname)`, you must provide an arg value for `hostname`.

.. code:: yaml

    schedule:
        ...
        args:
            hostname: server7.example.com

Some schedules can automatically provide certain args.  For example, the
`Interval schedule`_ provides the `time` arg automatically.  When Apsis creates
a run with this schedule, it provides a `time` arg with the (stringified) time
at which the job was scheduled.

If you don't need to provide any args, either because the job has no params, or
because all args are provided by the schedule, you can omit the `args` key.


Interval schedule
-----------------

An *interval schedule* (`type: interval`) schedules a run at regular intervals.
The interval is given in seconds.

.. code:: yaml

    schedule:
        type: interval
        interval: 14400  # every four hours

Apsis schedules a run for each time where `time % interval == 0`, where `time`
is the UTC time since epoch (1970-01-01T00:00:00+00:00).  To specify another
phase, give the `phase` key; its value is also in seconds.

The interval schedule will automatically provide an arg for a `time` param.  The
value for each run is the time for which the run scheduled.


Daily schedule
--------------

With a *daily schedule* (`type: daily`), Apsis schedules a run at a certain
daytime (time of day) every day.  You must provide the daytime, as well as the
time zone in which to interpret the daytime.

.. code:: yaml

    schedule:
        type: daily
        daytime: 10:30:00
        tz: Europe/Berlin

Apsis will schedule a run each day at 10:30 AM, Berlin time.

You can provide multiple daytimes.

.. code:: yaml

    schedule:
        type: daily
        daytime:
          - 10:30:00
          - 12:30:00
          - 16:30:00
        tz: Europe/Berlin

You can limit the dates that Apsis will schedule the run on, by specify a
_calendar_, which contains only certain dates.  For instances, the calendar
`Mon-Fri` contains all Mondays through Fridays, but not Saturdays or Sundays.

.. code:: yaml

    schedule:
        type: daily
        daytime: 10:30:00
        tz: Europe/Berlin
        calendar: Mon-Fri

Apsis gets calendars from Ora.  In addition to weekday calendars like `Thu`,
`Mon-Fri`, and `Tue,Thu`, you can provide your own custom calendars.  See `Ora's
calendar docs
<https://ora.readthedocs.io/en/latest/calendars.html#finding-calendars>`_ for
details.

The daily schedule will automatically provide args for `time` and `date`
params, using corresponding values.

Date shift
``````````

You can shift the schedule time for each run entire days backward or forward.
This will result in the schedule time for the run occurring on a different date
than the nominal date of the run, which is passed as the `date` arg.

For example, this job is scheduled to run at 20:00 UTC on the day before each
Monday, i.e. on each Sunday.  The `date` arg will always be a Monday, though.
For example, a run will be scheduled to start at 2020-11-09T20:00:00+00:00, but
its arg will be `date=2020-11-10`.

.. code:: yaml

    params: [date]

    schedule:
        type: daily
        daytime: 20:00:00
        tz: UTC
        calendar: Mon
        date_shift: -1


