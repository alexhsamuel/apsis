from   pathlib import Path
import pytest

from   apsis.output_db import OutputDB

#-------------------------------------------------------------------------------

def test0(tmpdir):
    db_path = Path(tmpdir) / "output-db"

    db = OutputDB.create(db_path)

    with pytest.raises(LookupError):
        db.get_metadata("r42")
    with pytest.raises(LookupError):
        db.get_data("r42", "output")

    data = b"The quick brown fox jumped over the lazy dogs.\x01\x02\x03"
    db.add_data("r42", "output", "combined output", data)

    meta = db.get_metadata("r42")
    assert list(meta.keys()) == ["output"]
    assert meta["output"]["name"] == "combined output"

    assert db.get_data("r42", "output") == data

    

