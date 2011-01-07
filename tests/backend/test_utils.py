import re
from nose.tools import with_setup

from fiftystates.backend import db, utils


@with_setup(db.legislators.drop)
def test_insert_with_id():
    obj1 = {'full_name': 'a test legislator',
           '_type': 'person',
           'state': 'ex'}
    obj2 = {'full_name': 'another legislator',
            '_type': 'person',
            'state': 'ex'}

    id_re = r'^EXL\d{6,6}$'
    
    id1 = utils.insert_with_id(obj1)
    assert re.match(id_re, id1)
    assert db.legislators.find_one({'_id': id1})

    id2 = utils.insert_with_id(obj2)
    assert re.match(id_re, id2)
    assert id2 != id1
    assert db.legislators.find_one({'_id': id2})
