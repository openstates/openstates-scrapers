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


def test_convert_timestamps():
    import time
    import datetime

    dt = datetime.datetime.now().replace(microsecond=0)
    ts = time.mktime(dt.utctimetuple())

    obj = {'date': ts,
           'actions': [{'when': ts}, {'date': ts}],
           'sources': [{'when': ts}, {'date': ts}],
           'votes': [{'when': ts}, {'date': ts}],
           'terms': [{'start_date': ts}, {'end_date': ts}],
           }

    expect = {'date': dt,
              'actions': [{'when': dt}, {'date': dt}],
              'sources': [{'when': dt}, {'date': dt}],
              'votes': [{'when': dt}, {'date': dt}],
              'terms': [{'start_date': dt}, {'end_date': dt}],
              }

    assert utils.convert_timestamps(obj) == expect

    # also modifies obj in place
    assert obj == expect
