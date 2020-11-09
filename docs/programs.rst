.. _programs:

Configurating Programs
======================

Apsis provides a number of ways to specify a job's program.  

A job's program is configured with the top-level `program` key.  The subkey
`type` indicates the program type; remaining keys are specific to the
configuration of each program type.


Shell commands
--------------

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


Programs
--------

The `program` program runs a process from an argument vector, skipping
execution through a shell.  Instead of a shell command, give `argv`, a list of
strings containing the arguments.  The first argument is the executable.

.. code:: yaml

    program:
        type: program
        argv:
        - /usr/bin/echo
        - Hello, world!

Since no shell evaluation takes place, there is no quoting, escaping, argument
splitting, or substitution.  Note Apsis still performs `Binding`_ on the `argv`
strings, as described above.


Users and hosts
---------------

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


