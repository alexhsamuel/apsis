from   functools import partial
import logging
import sys
import time

from   .instance import Instance
from   .instance_db import InstanceDB
from   .job import Job
from   .programmer import Programmer, program_instance_in
from   .scheduler import Scheduler, schedule_instance

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        style="{", 
        format="{asctime} [{levelname:8s}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger(None).setLevel(logging.DEBUG)

    job1 = Job(1, "/bin/sleep 1")
    job2 = Job(2, "echo 'job starting' pid=$$; /bin/sleep 2; echo 'job done' pid=$$")

    program_queue = []
    ready_queue = []
    schedule = partial(schedule_instance, ready_queue)
    db = InstanceDB("instance-db.pickle")

    programmer = Programmer(program_queue, schedule)
    scheduler = Scheduler(ready_queue, db)

    def program(job, interval):
        program_instance_in(program_queue, Instance(job), interval)

    program(job1,  1.0)
    program(job2,  0.5)
    program(job2, 10.0)
    
    for _ in range(300):
        programmer.run1()
        scheduler.run1()
        time.sleep(0.1)
    scheduler.run_all()


