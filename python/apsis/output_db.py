import gzip
import logging
from   pathlib import Path
import ujson

log = logging.getLogger(__name__)

#-------------------------------------------------------------------------------

# FIXME: Elsewhere.

def load_json_file(path: Path):
    with path.open("rt") as file:
        return ujson.load(file)


def dump_json_file(jso, path: Path):
    with path.open("wt") as file:
        ujson.dump(jso, file)


#-------------------------------------------------------------------------------

class OutputDB:

    @classmethod
    def create(Class, path):
        log.debug(f"create output DB: {path}")
        path.mkdir()
        return Class(path)


    def __init__(self, path: Path):
        self.__path = path


    def __get_meta_path(self, run_id) -> Path:
        return self.__path / run_id / "output.json"


    def __get_data_path(self, run_id, meta) -> Path:
        return self.__path / run_id / meta["filename"]


    def get_metadata(self, run_id) -> dict:
        """
        Returns output metadata for run `run_id`.
        """
        # FIXME: Sanitize run_id.
        meta_path = self.__get_meta_path(run_id)
        try:
            return load_json_file(meta_path)
        except FileNotFoundError:
            raise LookupError(f"no output for {run_id}")


    def get_data(self, run_id, output_id):
        try:
            meta = self.get_metadata(run_id)[output_id]
        except KeyError:
            raise LookupError(f"no output {output_id} for {run_id}")
            
        data_path = self.__get_data_path(run_id, meta)
        with gzip.open(data_path, "rb") as file:
            return file.read()


    def add_data(self, run_id: str, output_id: str, name: str, 
                 data: bytes):
        """
        Adds or replaces output `output_id` for `run_id`.
        """
        # Load metadata, or create the new run directory if this is a new run.
        meta_path = self.__get_meta_path(run_id)
        try:
            meta = load_json_file(meta_path)
        except FileNotFoundError:
            # New run.
            log.debug(f"new run dir: {meta_path.parent}")
            meta_path.parent.mkdir()
            meta = {}

        try:
            run_meta = meta[output_id]
        except KeyError:
            # New output.
            pass
        else:
            # Existing output.  Remove the old file.
            self.__get_data_path(run_id, run_meta).unlink()

        # Tack on the next metadata object.
        run_meta = meta[output_id] = {
            "name"          : name,
            # FIXME: Sanitize the name.
            "filename"      : output_id + ".gz",
            "content_type"  : "application/octet-stream",
        }
        
        # Write the data.
        data_path = self.__get_data_path(run_id, run_meta)
        with gzip.open(data_path, "wb") as file:
            file.write(data)

        # Rewrite the metedata.
        dump_json_file(meta, meta_path)



