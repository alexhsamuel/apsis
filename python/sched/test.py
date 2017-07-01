from   functools import partial
import logging
import sys
import time

from   .instance import Instance
from   .instance_db import InstanceDB
from   .job import Job
from   .scheduler import Scheduler, schedule_instance_in
from   .executor import Executor, execute_instance

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        style="{", 
        format="{asctime} [{levelname:8s}] {message}",
        datefmt="%Y-%m-%d %H:%M:%S")
    logging.getLogger(None).setLevel(logging.DEBUG)

    job1 = Job(1, "/bin/sleep 1")
    job2 = Job(2, "echo 'job starting' pid=$$; /bin/sleep 2; echo 'job done' pid=$$")

    schedule_queue = []
    execute_queue = []
    execute = partial(execute_instance, execute_queue)
    db = InstanceDB("instance-db.pickle")

    scheduler = Scheduler(schedule_queue, execute)
    executor = Executor(execute_queue, db)

    def schedule_in(job, interval):
        schedule_instance_in(schedule_queue, Instance(job), interval)

    schedule_in(job1,  1.0)
    schedule_in(job2,  0.5)
    schedule_in(job2, 10.0)
    
    for _ in range(300):
        scheduler.run1()
        executor.run1()
        time.sleep(0.1)
    executor.run_all()


