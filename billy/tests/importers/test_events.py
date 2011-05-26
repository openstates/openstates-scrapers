from nose.tools import with_setup

from billy import db
from billy.importers import events

def setup_func():
    db.events.drop()
    db.event_ids.drop()

@with_setup(setup_func)
def test_import_event_guid():
    event = {'level': 'state', 'state': 'ex', 'description': 'TBD',
             'when': 'now', 'end': 'never', 'type': 'party',
             '_guid': 'xx-yy-zz'}

    # test insert
    events.import_event(event)
    db_event = db.events.find_one({'_id': 'EXE00000001'})
    assert db_event['created_at'] == db_event['updated_at']
    assert db_event['description'] == 'TBD'

    # test update
    event['description'] = 'Determined.'
    events.import_event(event)
    assert db.events.count() == 1
    db_event = db.events.find_one({'_id': 'EXE00000001'})
    assert db_event['created_at'] < db_event['updated_at']
    assert db_event['description'] == 'Determined.'


@with_setup(setup_func)
def test_import_event_no_guid():
    event = {'level': 'state', 'state': 'ex', 'description': 'TBD',
             'when': 'now', 'end': 'never', 'type': 'party',}

    # test insert
    events.import_event(event)
    db_event = db.events.find_one({'_id': 'EXE00000001'})
    assert db_event['created_at'] == db_event['updated_at']
    assert db_event['description'] == 'TBD'

    # test update
    event['new_field'] = 'extra info'
    events.import_event(event)
    assert db.events.count() == 1
    db_event = db.events.find_one({'_id': 'EXE00000001'})
    assert db_event['created_at'] < db_event['updated_at']
    assert 'new_field' in db_event

    # update to description looks like new event without GUID
    event['description'] = 'break this thing'
    events.import_event(event)
    assert db.events.count() == 2
