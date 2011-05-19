from nose.tools import with_setup

from billy import db
from billy.importers import committees

def setup_func():
    db.metadata.drop()
    db.legislators.drop()
    db.committees.drop()

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
