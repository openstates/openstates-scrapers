import os
from billy import db
from billy.importers.metadata import import_metadata, PRESERVED_FIELDS

from nose.tools import with_setup

@with_setup(db.metadata.drop)
def test_import_metadata():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "fixture_data")
    import_metadata("ex", data_dir)
    metadata = db.metadata.find_one({"_id": "ex"})
    assert metadata
    assert metadata['_type'] == 'metadata'

    # add some fields
    for f in PRESERVED_FIELDS:
        metadata[f] = 'preserved'
    metadata['junk'] = 'goes away'
    db.metadata.save(metadata, safe=True)

    import_metadata("ex", data_dir)
    metadata = db.metadata.find_one({"_id": "ex"})
    for f in PRESERVED_FIELDS:
        assert f in metadata
    assert 'junk' not in metadata
