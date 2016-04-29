# jobs

A **job** has:

1. id
1. state
1. metadata for humans
1. schedule information
  - earliest time
  - latest time
1. retry specification

A job has this state model:

1. pending (??)
1. running
1. done&mdash;whether successful or not

State transitions proceed forward only.

A job instance, once created, can exist in one of these collections:

- the program: jobs whose programmed time hasn't arrived yet
- the blocked set: jobs which are blocked by some condition other than schedule
- the ready set: jobs that are ready to run
- the running set: jobs that are running
- the done set: jobs that have run

# actors

## programmer

The programmer monitors the program and wakes an instance when its start time arrives.  Woken instances are forwaded to the blocked set.

## coordinator

The coordinator monitors the blocked set and wakes an instance when all of its conditions are satified.  Woken instances are forwarded to the ready set.

## scheduler

The scheduler scheduls instances in the running set.  Scheduled instances are run.

## runner

The runner runs a job.  In addition it,

- Collects and records results.
- Transitions instance state.
- Applies retry logic by creating additional instances if necessary.

