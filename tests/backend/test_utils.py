import re
import time
import datetime

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


@with_setup(db.bills.drop)
def test_update():
    dt = datetime.datetime.utcnow()
    obj1 = {'_type': 'bill', 'state': 'ex', 'field1': 'stuff',
            'field2': 'original', '_locked_fields': 'field2',
            'created_at': dt, 'updated_at': dt}

    id1 = utils.insert_with_id(obj1)
    obj1 = db.bills.find_one(id1)

    # Updating a bill with itself shouldn't cause 'updated_at' to be changed
    utils.update(obj1, obj1, db.bills)
    obj2 = db.bills.find_one({'_id': id1})
    assert obj2['created_at'] == obj2['updated_at']
    assert obj1['updated_at'] == obj2['updated_at']

    utils.update(obj1, {'_type': 'bill', 'field1': 'more stuff',
                        'field2': 'a change', 'state': 'ex'},
                 db.bills)
    obj2 = db.bills.find_one({'_id': id1})
    assert obj2['created_at'] != obj2['updated_at']
    assert obj1['updated_at'] != obj2['updated_at']
    assert obj2['field1'] == 'more stuff'

    # make sure locked fields don't get overwritten
    assert obj2['field2'] == 'original'


def test_convert_timestamps():
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


def test_make_plus_fields():
    bill = {'_type': 'bill', 'bill_id': 'AB 123',
            'title': 'An Awesome Bill',
            'extra_field': 'this is not normal',
            'actions': [{'actor': 'Tom Cruise',
                         'action': 'hero',
                         'date': 'now',
                         'superfluous': 42}]}

    expect = {'_type': 'bill', 'bill_id': 'AB 123',
               'title': 'An Awesome Bill',
               '+extra_field': 'this is not normal',
               'actions': [{'actor': 'Tom Cruise',
                            'action': 'hero',
                            'date': 'now',
                            '+superfluous': 42}]}

    plussed = utils.make_plus_fields(bill)

    assert plussed == expect


def test_fix_bill_id():
    expect = 'AB 74'
    bill_ids = ['A.B. 74', 'A.B.74', 'AB74', 'AB 0074',
                'AB074', 'A.B.074', 'A.B. 074', 'A.B\t074']

    for bill_id in bill_ids:
        assert utils.fix_bill_id(bill_id) == expect
