import pytest

from   apsis.sqlite import SqliteDB

#-------------------------------------------------------------------------------

def test0():
    db = SqliteDB.create(path=None).output_db

    len(db.get_metadata("r42")) == 0

    with pytest.raises(LookupError):
        db.get_data("r42", "output")

    data = b"The quick brown fox jumped over the lazy dogs.\x01\x02\x03"
    db.add_data("r42", "output", "combined output", data)

    meta = db.get_metadata("r42")
    assert list(meta.keys()) == ["output"]
    assert meta["output"]["name"] == "combined output"

    assert db.get_data("r42", "output") == data

    

