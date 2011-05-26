from nose.tools import with_setup

from billy import db
from billy.importers import names


def setup_func():
    db.metadata.drop()
    db.legislators.drop()
    # TODO: this is kind of a hack, fix it?
    names.__matchers = {}


@with_setup(setup_func)
def test_get_legislator_id():
    db.metadata.insert({'_id': 'ex', 'level': 'state',
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
                                      'level': 'state',
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


@with_setup(setup_func)
def test_get_legislator_id_country():
    db.metadata.insert({'_id': 'zz',
                        'level': 'country',
                        'terms': [{'name': 'T1', 'sessions': ['S1']}]})
    db.legislators.insert({'_id': 'ZZL000042',
                           'level': 'country',
                           'country': 'zz',
                           'state': 'ab',
                           'full_name': 'Ed Iron Cloud III',
                           '_scraped_name': 'Ed Iron Cloud III',
                           'first_name': 'Ed',
                           'last_name': 'Iron Cloud',
                           'suffixes': 'III',
                           'roles': [{'type': 'member',
                                      'state': 'ab',
                                      'country': 'zz',
                                      'level': 'country',
                                      'term': 'T1',
                                      'chamber': 'upper',
                                      'district': '10'}]})

    assert names.get_legislator_id('zz', 'S1',
                                   'upper', 'Ed Iron Cloud') == 'ZZL000042'
    assert names.get_legislator_id('zz', 'S1',
                                   'upper', 'Iron Cloud') == 'ZZL000042'
    assert names.get_legislator_id('zz', 'S1',
                                   'upper', 'E. Iron Cloud') == 'ZZL000042'
    assert not names.get_legislator_id('zz', 'S1', 'lower', 'Ed Iron Cloud')
