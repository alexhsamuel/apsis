from   contextlib import closing, contextmanager
import logging
from   pathlib import Path
import pytest
import signal
import sqlite3
import subprocess
import tempfile
import time
import ujson
import yaml

#-------------------------------------------------------------------------------

def run_apsisctl(*argv):
    subprocess.run(["apsisctl", *( str(a) for a in argv )], check=True)


class ApsisInstance:

    def __init__(self, *, port=5005):
        self.port       = int(port)

        self.tmp_dir    = Path(tempfile.mkdtemp())
        logging.info(f"Apsis instance in {self.tmp_dir}")
        self.db_path    = self.tmp_dir / "apsis.db"
        self.jobs_dir   = self.tmp_dir / "jobs"
        self.cfg_path   = self.tmp_dir / "config.yaml"
        self.log_path   = self.tmp_dir / "apsis.log"

        self.cfg        = None
        self.srv_proc   = None


    def create_db(self):
        run_apsisctl("create", self.db_path)


    def write_cfg(self, cfg):
        self.cfg = {
            "database": str(self.db_path),
            "jobs": str(self.jobs_dir),
            **cfg
        }
        with open(self.cfg_path, "w") as file:
            yaml.dump(cfg, file)

        
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
            ret = self.srv_proc.wait(timeout=0)
        except subprocess.TimeoutExpired as exc:
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


    def run_apsis_json(self, *argv):
        """
        Runs an `apsis` subcommand against the running service.

        Requests JSON output, and parses it.

        :return:
          The return code, and the parsed JSO output.
        """
        assert self.srv_proc is not None
        argv = [
            "apsis",
            "--port", str(self.port),
            *( str(a) for a in argv ),
            "--format", "json"
        ]
        proc = subprocess.run(argv, stdout=subprocess.PIPE)
        logging.info(f"apsis returned: {proc.returncode} {proc.stdout}")
        return proc.returncode, ujson.loads(proc.stdout)



@pytest.fixture(scope="module")
def inst():
    with closing(ApsisInstance()) as inst:
        yield inst


#-------------------------------------------------------------------------------

def test_create_db(inst):
    inst.create_db()
    assert inst.db_path.is_file()
    with sqlite3.connect(inst.db_path) as db:
        with closing(db.cursor()) as cursor:
            cursor.execute("SELECT * FROM runs")
            names = { d[0] for d in cursor.description }
            assert "run_id" in names
            assert len(list(cursor)) == 0


def test_cfg(inst):
    inst.write_cfg({})
    assert inst.cfg_path.is_file()
    with open(inst.cfg_path) as file:
        yaml.load(file, yaml.SafeLoader)


def test_start_serve(inst):
    inst.start_serve()
    inst.wait_for_serve()


def test_jobs_empty(inst):
    ret, out = inst.run_apsis_json("jobs")
    assert ret == 0
    assert len(out) == 0


def test_stop_serve(inst):
    ret = inst.stop_serve()
    assert ret == 0


