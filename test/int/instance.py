from   contextlib import contextmanager
import logging
from   pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import ujson
import yaml

#-------------------------------------------------------------------------------

def run_apsisctl(*argv):
    subprocess.run(["apsisctl", *( str(a) for a in argv )], check=True)


class ApsisInstance:

    # FIXME: Choose an available port.
    def __init__(self, *, port=5005, job_dir=None):
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

        self.cfg        = None
        self.srv_proc   = None


    def create_db(self):
        run_apsisctl("create", self.db_path)


    def write_cfg(self, cfg={}):
        self.cfg = {
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
                    "--log", "INFO",
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


    @contextmanager
    def get_log(self):
        with open(self.log_path) as file:
            yield iter(file)


    def stop_serve(self):
        assert self.srv_proc is not None
        self.srv_proc.send_signal(signal.SIGTERM)
        return self.srv_proc.wait()


    def close(self):
        if self.srv_proc is not None:
            self.stop_serve()
            with open(self.log_path) as file:
                sys.stdout.write(file.read())


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



