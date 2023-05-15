.. _programs:

Configurating Programs
======================

Apsis provides a number of ways to specify a job's program.  

A job's program is configured with the top-level `program` key.  The subkey
`type` indicates the program type; remaining keys are specific to the
configuration of each program type.

Apsis provides these program types, and you can extend Apsis with your own.

- `no-op`: Does nothing.
- `shell`: Executes a shell command, possibly on another host.
- `program`: Invokes an executable directly, with command line arguments.

Additionally, Apsis includes several internal program types, which deal with its
own internal housekeeping.


No-op programs
--------------

A `no-op` program runs instantly and always succeeds.

.. code:: yaml

    program:
        type: no-op


Running other programs
----------------------

Shell commands
^^^^^^^^^^^^^^

The `shell` program executes shell command, given in the `command` key. 

.. code:: yaml

    program:
        type: shell
        command: /usr/bin/echo 'Hello, world!'

Note the following:

- The command is a string.  YAML provides multiple syntaxes for specifying
  strings, each with different rules for line breaks, whitespace, and special
  characters.  See, for example,
  `yaml-multiline.info <https://yaml-multiline.info/>`_.

- The command actually a short program, executed by a new shell instance.
  The shell is
  `bash <https://www.gnu.org/software/bash/manual/bash.html>`_.  All shell
  quoting, escaping, variable expansion, etc. rules apply.

- The command may be multiline, execute multiple programs, use shell flow
  control constructs, etc.

- Binding happens after the YAML is parsed by Apsis (when job config is loaded),
  but before the shell interprets the command (when a run starts).


Argv invocations
^^^^^^^^^^^^^^^^

The `program` program invokes an executable directly, without starting a shell.
Instead of a shell command, give `argv`, a list of strings containing the
arguments.  The first argument is the executable.

.. code:: yaml

    program:
        type: program
        argv:
        - /usr/bin/echo
        - Hello, world!

Since no shell evaluation takes place, there is no quoting, escaping, argument
splitting, or substitution.  Note Apsis still performs :doc:`binding <./jobs>` on the `argv`
strings, as described above.


Users and hosts
^^^^^^^^^^^^^^^

Apsis can run shell commands and programs as another user, or on another host.
Specify the `user` and `host` keys.

.. code:: yaml

    program:
        type: shell
        user: devacct
        host: dev3.example.net
        command: >
            echo I am $(whoami) and I am running on $(hostname -s). 

The `host` key may specify any host name understood by SSH, or a host group
name.  Host groups are configured in the Apsis config file.

The remote program is launched via SSH and monitored by an agent program.

FIXME: Document this better.


Timeouts
^^^^^^^^

You can specify a timeout duration for shell command or program.  If the timeout
elapses before the program completes, Apsis sends the program a signal.

.. code:: yaml

    program:
        type: shell
        command: /usr/bin/takes-too-long
        timeout:
            duration: 300
            signal: SIGTERM

In this example, Apsis sends SIGTERM to the program after five minutes, if it
hasn't completed yet.  The `signal` key is optional and defaults to SIGTERM.


Internal Programs
-----------------

An *internal program* is a special program that operates on Apsis itself.  These
internal program types are available:


Stats
^^^^^

A `apsis.program.internal.stats` program generates internal statistics about
Apsis's state and resource use, in JSON format.  Stats are generated as program
output.  If you specify the `path` key, the JSON stats are also appended, with a
newline, to the specified file.

This job produces a run once a minute, which appends the stats to a dated file:

.. code:: yaml

    params: [date]

    schedule:
        type: interval
        interval: 60

    program:
        type: apsis.program.internal.stats.StatsProgram
        path: "/path/to/apsis/stats/{{ date }}.json"



Archive
^^^^^^^

A `apsis.program.interal.archive` program moves data pertaining to older runs
out of the Apsis database file, into a separate archive file.  Keeping the main
Apsis database file from growing too large can avoid performance degredation.

The archive program retires a run from Apsis's memory before archiving it.  The
run is no longer visible through any UI.  A run that is not completed cannot be
archived.

This job archives up to 10,000 runs older than 14 days (1,209,600 seconds):

.. code:: yaml

    schedule:
        type: daily
        tz: UTC
        time: 01:30:00

    program:
        type: apsis.program.internal.archive.ArchiveProgram
        age: 1209600
        count: 10000
        path: '/path/to/apsis/archive.db'

The archive program blocks Apsis from performing other tasks.  Adjust the
`count` parameter so that the archiving process does not take more than a few
seconds, to avoid long delays in startng scheduled runs.

The archive file is also an SQLite3 database file, and contains the subset of
columns from the main database file that contains run data.  The archive file
cannot be used directly by Apsis, but may be useful for historical analysis and
forensics.

