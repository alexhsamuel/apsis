from   contextlib import contextmanager
import functools
import logging
from   pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import ujson
import yaml

import apsis.service.client
from   apsis.sqlite import SqliteDB

#-------------------------------------------------------------------------------

def run_apsisctl(*argv):
    subprocess.run(["apsisctl", *( str(a) for a in argv )], check=True)


class ApsisInstance:

    # FIXME: Choose an available port.
    def __init__(self, *, port=5005, job_dir=None, cfg={}):
        self.port       = int(port)

        self.tmp_dir    = Path(tempfile.mkdtemp())
        logging.info(f"Apsis instance in {self.tmp_dir}")
        self.db_path    = self.tmp_dir / "apsis.db"
        self.jobs_dir   = (
            Path(job_dir) if job_dir is not None
            else self.tmp_dir / "jobs"
        )
        self.cfg_path   = self.tmp_dir / "config.yaml"
        self.log_path   = self.tmp_dir / "apsis.log"

        self.cfg        = dict(cfg)
        self.srv_proc   = None


    def create_db(self):
        SqliteDB.create(self.db_path)


    # FIXME: Remove cfg param.
    def write_cfg(self, cfg={}):
        self.cfg |= {
            "database": str(self.db_path),
            "job_dir": str(self.jobs_dir),
            **cfg
        }
        with open(self.cfg_path, "w") as file:
            yaml.dump(self.cfg, file)


    def start_serve(self):
        assert self.cfg is not None
        assert self.srv_proc is None

        with open(self.log_path, "w") as log_file:
            self.srv_proc = subprocess.Popen(
                [
                    "apsisctl",
                    "--log", "DEBUG",
                    "serve",
                    "--config", str(self.cfg_path),
                    "--port", str(self.port),
                ],
                stderr=log_file
            )


    def wait_for_serve(self):
        # FIXME: This is horrible.
        while True:
            assert self.is_running()
            with self.get_log() as log:
                if any( "service ready to run" in l for l in log ):
                    return True
            time.sleep(1)


    def is_running(self):
        if self.srv_proc is None:
            return False
        try:
            self.srv_proc.wait(timeout=0)
        except subprocess.TimeoutExpired:
            return True
        else:
            return False


    @functools.cached_property
    def client(self):
        return apsis.service.client.Client(("localhost", self.port))


    @contextmanager
    def get_log(self):
        with open(self.log_path) as file:
            yield iter(file)


    def get_log_lines(self):
        with self.get_log() as lines:
            return tuple(lines)


    def stop_serve(self):
        assert self.srv_proc is not None
        self.srv_proc.send_signal(signal.SIGTERM)
        return self.srv_proc.wait()


    def close(self):
        if self.srv_proc is not None:
            self.stop_serve()
            with open(self.log_path) as file:
                sys.stdout.write(file.read())
            sys.stdout.flush()


    def run_apsis_cmd(self, *argv):
        """
        Runs an `apsis` subcommand against the running service.

        :return:
          The return code and stdout.
        """
        assert self.srv_proc is not None
        argv = [
            "apsis",
            "--port", str(self.port),
            *( str(a) for a in argv )
        ]
        proc = subprocess.run(argv, stdout=subprocess.PIPE)
        logging.info(f"apsis returned: {proc.returncode} {proc.stdout}")
        return proc.returncode, proc.stdout


    def run_apsis_json(self, *argv):
        """
        Runs an `apsis` subcommand against the running service.

        Requests JSON output, and parses it.

        :return:
          The parsed JSO output.
        """
        returncode, stdout = self.run_apsis_cmd(*argv, "--format", "json")
        assert returncode == 0, \
            f"'apsis {' '.join(argv)}' failed: {stdout.decode()}"
        return ujson.loads(stdout)


    def wait_run(self, run_id, *, wait_states=("new", "scheduled", "waiting", "starting", "running")):
        """
        Polls for a run to no longer be running.
        """
        for _ in range(600):
            res = self.client.get_run(run_id)
            if res["state"] in wait_states:
                time.sleep(0.1)
                continue
            else:
                return res
        else:
            raise RuntimeError("timeout waiting for run")


    def wait_for_run_to_start(self, run_id):
        return self.wait_run(run_id, wait_states=("new", "scheduled", "waiting", "starting"))


