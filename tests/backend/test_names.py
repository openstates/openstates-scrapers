from nose.tools import with_setup

from fiftystates.backend import db, names


def setup_func():
    db.legislators.drop()
    db.metadata.drop()


@with_setup(setup_func)
def test_get_legislator_id():
    db.metadata.insert({'_id': 'ex',
                        'terms': [{'name': 'T1',
                                   'sessions': ['S1']}]})
    db.legislators.insert({'_id': 'EXL000042',
                           'state': 'ex',
                           'full_name': 'Ed Iron Cloud III',
                           '_scraped_name': 'Ed Iron Cloud III',
                           'first_name': 'Ed',
                           'last_name': 'Iron Cloud',
                           'suffixes': 'III',
                           'roles': [{'type': 'member',
                                      'state': 'ex',
                                      'term': 'T1',
                                      'chamber': 'upper',
                                      'district': '10'}]})

    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'Ed Iron Cloud') == 'EXL000042'
    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'Iron Cloud') == 'EXL000042'
    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'E. Iron Cloud') == 'EXL000042'
    assert not names.get_legislator_id('ex', 'S1', 'lower', 'Ed Iron Cloud')
