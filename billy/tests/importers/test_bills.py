import copy
from billy import db
from billy.importers import bills, names

from nose.tools import with_setup

def setup_func():
    db.metadata.drop()
    db.bills.drop()
    db.legislators.drop()
    db.vote_ids.drop()
    names.__matchers = {}

    db.metadata.insert({'_level': 'state', '_id': 'ex',
                        'terms': [{'name': 'T1', 'sessions': ['S1', 'S2']}]})
    db.legislators.insert({'_level': 'state', 'state': 'ex',
                           '_id': 'EXL000001', 'leg_id': 'EXL000001',
                           'chamber': 'upper',
                           'full_name': 'John Adams', 'first_name': 'John',
                           'last_name': 'Adams', '_scraped_name': 'John Adams',
                           'roles': [
                               {'type': 'member', 'chamber': 'upper',
                                'term': 'T1', 'state': 'ex'},
                           ]
                          })


@with_setup(setup_func)
def test_import_bill():
    data = {'_type': 'bill', '_level': 'state', 'state': 'ex', 'bill_id': 'S1',
            'chamber': 'upper', 'session': 'S1',
            'subjects': ['Pigs', 'Sheep', 'Horses'],
            'sponsors': [{'name': 'Adams', 'type': 'primary'},
                         {'name': 'Jackson', 'type': 'cosponsor'}],
            'title': 'main title',
            'alternate_titles': ['second title'],
            'versions': [{'title': 'old title'},
                         {'title': 'main title'}],
            'votes': [{'motion': 'passage', 'chamber': 'upper', 'date': None,
                       'yes_count': 1, 'no_count': 1, 'other_count': 0,
                       'yes_votes': ['John Adams'],
                       'no_votes': ['John Quincy Adams'],
                       'other_votes': [],
                      },
                      {'motion': 'referral', 'chamber': 'upper', 'date': None,
                       'yes_count': 0, 'no_count': 0, 'other_count': 0,
                       'yes_votes': [], 'no_votes': [], 'other_votes': [],
                       'committee': 'Committee on Agriculture',
                      }],
           }
    standalone_votes = {
        # chamber, session, bill id -> vote list
        ('upper', 'S1', 'S 1'): [
          {'motion': 'house passage', 'chamber': 'lower', 'date': None,
           'yes_count': 1, 'no_count': 0, 'other_count': 0,
           'yes_votes': [], 'no_votes': [], 'other_votes': [],
          }
        ]
    }

    # deepcopy both so we can reinsert same data without modification
    bills.import_bill(copy.deepcopy(data), copy.deepcopy(standalone_votes))

    # test that basics work
    bill = db.bills.find_one()
    assert bill['bill_id'] == 'S 1'
    assert bill['chamber'] == 'upper'
    assert bill['scraped_subjects'] == data['subjects']
    assert 'subjects' not in bill
    assert bill['_term'] == 'T1'
    assert '_keywords' in bill
    assert bill['created_at'] == bill['updated_at']

    # assure sponsors are there and that John Adams gets matched
    assert len(bill['sponsors']) == 2
    assert bill['sponsors'][0]['leg_id'] == 'EXL000001'

    # test vote import
    assert len(bill['votes']) == 3
    assert bill['votes'][0]['vote_id'] == 'EXV00000001'
    assert bill['votes'][0]['yes_votes'][0]['leg_id'] == 'EXL000001'
    assert 'committee_id' in bill['votes'][1]

    # titles from alternate_titles & versions (not main title)
    assert 'main title' not in bill['alternate_titles']
    assert 'second title' in bill['alternate_titles']
    assert 'old title' in bill['alternate_titles']

    # now test an update
    data['versions'].append({'title': 'third title'})
    data['sponsors'].pop()
    bills.import_bill(data, standalone_votes)

    # still only one bill
    assert db.bills.count() == 1
    bill = db.bills.find_one()

    # votes haven't changed, versions, titles, and sponsors have
    assert len(bill['votes']) == 3
    assert bill['votes'][0]['vote_id'] == 'EXV00000001'
    assert len(bill['versions']) == 3
    assert len(bill['sponsors']) == 1
    assert 'third title' in bill['alternate_titles']


def test_fix_bill_id():
    expect = 'AB 74'
    bill_ids = ['A.B. 74', 'A.B.74', 'AB74', 'AB 0074',
                'AB074', 'A.B.074', 'A.B. 074', 'A.B\t074']

    for bill_id in bill_ids:
        assert bills.fix_bill_id(bill_id) == expect

    assert bills.fix_bill_id('PR19-0041') == 'PR 19-0041'



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

    bills.populate_current_fields('state', 'ex')

    b = db.bills.find_one({'title': 'current everything'})
    assert b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'current term'})
    assert not b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'not current'})
    assert not b['_current_session']
    assert not b['_current_term']


@with_setup(db.vote_ids.drop)
def test_votematcher():
    # three votes, two with the same fingerprint
    votes = [{'motion': 'a', 'chamber': 'b', 'date': 'c',
             'yes_count': 1, 'no_count': 2, 'other_count': 3},
             {'motion': 'x', 'chamber': 'y', 'date': 'z',
             'yes_count': 0, 'no_count': 0, 'other_count': 0},
             {'motion': 'a', 'chamber': 'b', 'date': 'c',
             'yes_count': 1, 'no_count': 2, 'other_count': 3},
            ]
    vm = bills.VoteMatcher('ex')

    vm.set_vote_ids(votes)
    assert votes[0]['vote_id'] == 'EXV00000001'
    assert votes[1]['vote_id'] == 'EXV00000002'
    assert votes[2]['vote_id'] == 'EXV00000003'

    # a brand new matcher has to learn first
    vm = bills.VoteMatcher('ex')
    vm.learn_vote_ids(votes)

    # clear vote_ids & add a new vote
    for v in votes:
        v.pop('vote_id', None)
    votes.insert(2, {'motion': 'f', 'chamber': 'g', 'date': 'h',
                  'yes_count': 5, 'no_count': 5, 'other_count': 5})

    # setting ids now should restore old ids & give the new vote a new id
    vm.set_vote_ids(votes)
    assert votes[0]['vote_id'] == 'EXV00000001'
    assert votes[1]['vote_id'] == 'EXV00000002'
    assert votes[2]['vote_id'] == 'EXV00000004'
    assert votes[3]['vote_id'] == 'EXV00000003'
