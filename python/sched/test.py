import logging
import random
import sys
import time

from   .instance import Instance
from   .instance_db import InstanceDB
from   .job import Job
from   .scheduler import Scheduler

if __name__ == "__main__":
    logging.getLogger(None).setLevel(logging.DEBUG)

    job1 = Job(1, "/bin/sleep 1")
    job2 = Job(2, "echo 'job starting' pid=$$; /bin/sleep 2; echo 'job done' pid=$$")

    ready_queue = []
    db = InstanceDB("instance-db.pickle")

    def start_job(job):
        instance = Instance(job, random.randint(0, sys.maxsize))
        db.create_instance(instance)
        ready_queue.append(instance)

    sched = Scheduler(ready_queue, db)

    start_job(job2)
    start_job(job1)
    start_job(job2)

    for _ in range(15):
        sched.run1()
        time.sleep(0.1)

    start_job(job1)
    start_job(job2)

    sched.run_all()
