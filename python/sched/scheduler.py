import errno
import logging
import os
import signal
import subprocess
import sys
import time

#-------------------------------------------------------------------------------

def _start(job):
    proc = subprocess.Popen(job.command, shell=True)
    return proc


class Scheduler:

    def __init__(self, ready_queue, instance_db):
        self.__ready_queue = ready_queue
        self.__instance_db = instance_db

        # Map from pid to subprocess.Popen for running processes.
        self.__procs = {}
        # Finished child pids.
        self.__done_pids = {}

        # Register our SIGCHLD handler.
        # FIXME: Don't monopolize the handler.
        signal.signal(signal.SIGCHLD, self.__sigchld)


    # FIXME: Do we need to trap SIGCHLD if we're wait4(-1)ing regularly?
    def __sigchld(self, signum, frame):
        assert signum == signal.SIGCHLD
        while True:
            try:
                pid, status, usage = os.wait4(-1, os.WNOHANG)
            except ChildProcessError as exc:
                if exc.errno == errno.ECHILD:
                    # No (more) children.
                    break
                else:
                    raise
            else:
                if pid == 0:
                    # No zombie children.
                    break
                else:
                    logging.debug("child {} terminated".format(pid))
                    self.__done_pids[pid] = status, usage


    def run1(self):
        # Process terminated instances.
        while len(self.__done_pids) > 0:
            pid, (status, usage) = self.__done_pids.popitem()
            proc = self.__procs.pop(pid)
            instance = proc.instance
            self.__instance_db.set_result(instance, (status, usage))
            logging.debug("instance {:x} done".format(instance.id))

        # Start ready instances.
        while len(self.__ready_queue) > 0:
            instance = self.__ready_queue.pop()
            logging.debug("starting instance {:x}".format(instance.id))
            proc = _start(instance.job)
            logging.debug(
                "child {} started for instance {:x}"
                .format(proc.pid, instance.id))

            proc.instance = instance
            self.__procs[proc.pid] = proc


    def run_all(self, interval=0.1):
        while len(self.__ready_queue) > 0 or len(self.__procs) > 0:
            self.run1()
            # FIXME: Hacky.
            time.sleep(interval)
        logging.debug("no ready or running jobs")



