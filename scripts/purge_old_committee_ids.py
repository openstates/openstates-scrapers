from billy.core import db, feeds_db
from billy.core import settings
from billy.core import logging


def main():

    import sys
    abbrs = sys.argv[1:] or [x['abbreviation'] for x in db.metadata.find()]
    logger = logging.getLogger('purge_committee_ids')
    logger.setLevel(logging.DEBUG)

    for abbr in abbrs:
        spec = {settings.LEVEL_FIELD: abbr}
        committee_ids = [c['_id'] for c in db.committees.find(spec, fields=['_id'])]

        # Events with committee participants.
        spec = {
            settings.LEVEL_FIELD: abbr,
            'participants.committee_id': {'$nin': committee_ids}
            }
        for event in db.events.find(spec):
            old_ids = set()
            count = 0
            found = False
            for participant in event['participants']:
                for id_key in 'committee_id', 'id':
                    _id = participant.get(id_key, None)
                    type_ = participant.get('participant_type')
                    if id_key == 'id' and type_ != 'committee':
                        continue
                    if _id and (_id not in committee_ids):
                        found = True
                        msg = 'Removing participant %r from event %r'
                        logger.info(msg % (participant[id_key], event['_id']))

                        # Leave the participant in but set their id to none.
                        # Text will still be displayed without a hyperlink.
                        participant[id_key] = None

            if found:
                msg = 'Removed %d old committee %r ids from %r'
                logger.info(msg % (count, old_ids, event['_id']))
                db.events.save(event, safe=True)

        # Related committees in bill actions.
        spec = {
            settings.LEVEL_FIELD: abbr,
            'actions.related_entities.type': 'committee'
            }
        for bill in db.bills.find(spec):
            old_ids = set()
            count = 0
            found = False
            for action in bill['actions']:
                for entity in action['related_entities']:
                    if entity['type'] == 'committee':
                        if entity['id'] and (entity['id'] not in committee_ids):
                            found = True
                            count += 1
                            old_ids.add(entity['id'])
                            msg = 'Removing entity %r from action in %r'
                            logger.debug(msg % (entity['id'], bill['bill_id']))

                            # Completely remove the related entity. Without an
                            # id it has no other purpose.
                            action['related_entities'].remove(entity)
            if found:
                msg = 'Removed %d old committee %r ids from %r'
                logger.info(msg % (count, old_ids, bill['_id']))
                db.bills.save(bill, safe=True)

        # Legislator old roles.
        spec = {
            settings.LEVEL_FIELD: abbr,
            'old_roles': {'$exists': True}
            }
        for leg in db.legislators.find(spec):
            old_ids = set()
            count = 0
            found = False
            for role in leg['old_roles']:
                if 'committee_id' in role:
                    _id = role['committee_id']
                    if _id and (_id not in committee_ids):
                        found = True
                        count += 1
                        old_ids.add(_id)
                        msg = 'Removing id %r from old_role in %r'
                        logger.info(msg % (role['committee_id'], leg['full_name']))
                        # Set the id to None.
                        role['committee_id'] = None
            if found:
                msg = 'Removed %d old committee %r ids from %r'
                logger.info(msg % (count, old_ids, leg['_id']))
                db.legislators.save(leg, safe=True)

        # Related entities in feeds.
        spec = {
            settings.LEVEL_FIELD: abbr,
            'entity_ids': {'$ne': None}
            }
        for entry in feeds_db.entries.find(spec):
            old_ids = set()
            count = 0
            found = False
            for entity_id in entry['entity_ids']:
                if entity_id[2] == 'C':
                    if entity_id not in committee_ids:
                        found = True
                        count += 1
                        msg = 'Removing id %r from feed %r'
                        logger.info(msg % (entity_id, entry['_id']))

                        # Delete the entity from the feed.
                        old_ids.add(entity_id)
                        index = entry['entity_ids'].index(entity_id)
                        del entry['entity_ids'][index]
                        del entry['entity_strings'][index]
            if found:
                msg = 'Removed %d old committee ids %r from %r'
                logger.info(msg % (count, old_ids, entry['_id']))
                feeds_db.entries.save(entry, safe=True)

        # Nuke any committee sponsors of bills.
        spec = {
            settings.LEVEL_FIELD: abbr,
            'sponsors.committee_id': {'$nin': committee_ids}
            }
        for bill in db.bills.find(spec):
            count = 0
            found = False
            old_ids = set()
            for sponsor in bill.get('sponsors', []):
                if 'committee_id' in sponsor:
                    _id = sponsor['committee_id']
                    old_ids.add(_id)
                    found = True
                    count += 1

                    del sponsor['committee_id']

            if found:
                msg = 'Removed %d old committee ids %r from %r'
                logger.info(msg % (count, old_ids, bill['_id']))
                db.bills.save(bill)

if __name__ == '__main__':
    main()
