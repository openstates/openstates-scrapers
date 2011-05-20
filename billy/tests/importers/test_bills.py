from billy import db
from billy.importers import bills

from nose.tools import with_setup

def setup_func():
    db.metadata.drop()
    db.bills.drop()

    db.metadata.insert({'_level': 'state', '_id': 'ex',
                        'terms': [{'name': 'T1', 'sessions': ['S1', 'S2']}]})

def test_bill_keywords():
    bill = {'title': 'transportation of hazardous materials',
            'bill_id': 'HB 201',
            'alternate_titles': [
                'cephalopod waste disposal',
                'elimination of marine garbage'
            ]}
    expected = set(['201', 'elimin', 'garbag', 'materi', 'wast', 'hazard',
                    'marin', 'hb', 'dispos', 'cephalopod', 'transport'])
    assert bills.bill_keywords(bill) == expected

@with_setup(setup_func)
def test_populate_current_fields():
    db.bills.insert({'_level': 'state', 'state': 'ex', 'session': 'S1',
                     'title': 'current term'})
    db.bills.insert({'_level': 'state', 'state': 'ex', 'session': 'S2',
                     'title': 'current everything'})
    db.bills.insert({'_level': 'state', 'state': 'ex', 'session': 'S0',
                     'title': 'not current'})

    bills.populate_current_fields('ex')

    b = db.bills.find_one({'title': 'current everything'})
    assert b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'current term'})
    assert not b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'not current'})
    assert not b['_current_session']
    assert not b['_current_term']
