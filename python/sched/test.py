import logging
import random
import sys
import time

from   .instance import Instance
from   .instance_db import InstanceDB
from   .job import Job
from   .scheduler import Scheduler, schedule_job

if __name__ == "__main__":
    logging.getLogger(None).setLevel(logging.DEBUG)

    job1 = Job(1, "/bin/sleep 1")
    job2 = Job(2, "echo 'job starting' pid=$$; /bin/sleep 2; echo 'job done' pid=$$")

    ready_queue = []
    db = InstanceDB("instance-db.pickle")

    sched = Scheduler(ready_queue, db)
    schedule = lambda job: schedule_job(ready_queue, job)

    schedule(job2)
    schedule(job1)
    schedule(job2)

    for _ in range(15):
        sched.run1()
        time.sleep(0.1)

    schedule(job1)
    schedule(job2)

    sched.run_all()


