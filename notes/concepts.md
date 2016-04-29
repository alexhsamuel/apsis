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

- the program queue: jobs whose programmed time hasn't arrived yet
- the blocked queue: jobs which are blocked by some condition other than schedule
- the ready queue: jobs that are ready to run
- the running queue: jobs that are running

# actors

## programmer

The programmer monitors the program queue and wakes an instance when its start time arrives.  Woken instances are forwaded to the blocked queue.

## coordinator

The coordinator monitors the blocked queue and wakes an instance when all of its conditions are satified.  Woken instances are forwarded to the queue set.

## scheduler

The scheduler runs instances in the running queue.  In addition it,

- Maintains the ready and running queues.
- Collects and records results.
- Transitions instance state.
- Applies retry logic by creating additional instances if necessary.

