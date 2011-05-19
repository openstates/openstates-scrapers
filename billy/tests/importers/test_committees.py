from nose.tools import with_setup

from billy import db
from billy.importers import committees
from billy.importers import names

def setup_func():
    db.metadata.drop()
    db.legislators.drop()
    db.committees.drop()

    db.metadata.insert({'_level': 'state', '_id': 'ex',
                        'terms': [{'name': 'T1', 'sessions': ['S1']}]})

    leg_a = {'full_name': 'Richard Feynman', 'leg_id': 'EXL000001',
             '_level': 'state',
             'roles': [
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member',  'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member',  'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
              ]}
    leg_b = {'full_name': 'Albert Einstein', 'leg_id': 'EXL000002',
             '_level': 'state',
             'roles': [
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'position': 'chairman',
                  'type': 'committee member',  'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                 'type': 'committee member',  'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member',  'committee': 'Appropriations'},
              ]}
    # in a different term
    leg_c = {'full_name': 'Werner Heisenberg', 'leg_id': 'EXL000003',
             '_level': 'state',
             'roles': [
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Appropriations'},
              ]}

    db.legislators.insert(leg_a)
    db.legislators.insert(leg_b)
    db.legislators.insert(leg_c)

@with_setup(setup_func)
def test_committees_from_legislators():
    committees.import_committees_from_legislators('T1', 'state', 'ex')

    # 3 overall
    assert db.committees.count() == 3

    ag_com = db.committees.find_one({'_id': 'EXC000001'})
    assert ag_com['subcommittee'] == None
    assert ag_com['members'][0]['leg_id'] == 'EXL000001'
    # Heisenberg isn't added (wrong term)
    assert len(ag_com['members']) == 2
    assert ag_com['members'][0]['role'] == 'member'
    # check that position is copied over
    assert ag_com['members'][1]['role'] == 'chairman'

    # subcommittee
    tractor_subcom = db.committees.find_one({'subcommittee': 'Tractors'})
    assert tractor_subcom['committee'] == 'Agriculture'
    assert tractor_subcom['_id'] == 'EXC000002'

    # make sure that committee_ids are added to legislators
    feynman = db.legislators.find_one({'leg_id': 'EXL000001'})
    assert 'committee_id' in feynman['roles'][1]

@with_setup(setup_func)
def test_import_committee():
    committee = {'_type': 'committee', '_level': 'state', 'state': 'ex',
                 'chamber': 'joint', 'committee': 'Reptilian Task Force',
                 'members': [
                     {'name': 'Richard Feynman'},
                     {'name': 'A. Einstein'},
                 ]
                }

    committees.import_committee(committee, 'S1', 'T1')

    com = db.committees.find_one()

    assert com

    # for some reason this test makes test_names fail
