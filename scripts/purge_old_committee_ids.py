import pprint

from billy.core import db
from billy.core import settings
from billy.core import logging


def main():

    import sys
    abbr = sys.argv[1]

    logger = logging.getLogger('purge_committee_ids')
    spec = {settings.LEVEL_FIELD: abbr}
    committee_ids = [c['_id'] for c in db.committees.find(spec, fields=['_id'])]

    # Events with committee participants.
    spec = {
        settings.LEVEL_FIELD: abbr,
        'participants.committee_id': {'$nin': committee_ids}
        }
    for event in db.events.find(spec):
        found = False
        for participant in event['participants']:
            _id = participant.get('committee_id', None)
            if _id and (_id not in committee_ids):
                found = True
                msg = 'Removing participant %r from event %r'
                logger.info(msg % (participant['committee_id'], event['_id']))
                event['participants'].remove(participant)
        if found:
            import ipdb;ipdb.set_trace()

    # Bill actions.
    spec = {
        settings.LEVEL_FIELD: abbr,
        'actions.related_entities.type': 'committee'
        }
    for bill in db.bills.find(spec):
        # pprint.pprint(bill['actions'])
        found = False
        for action in bill['actions']:
            for entity in action['related_entities']:
                if entity['type'] == 'committee':
                    if entity['id'] not in committee_ids:
                        found = True

                        msg = 'Removing entity %r from action in %r'
                        logger.info(msg % (entity['id'], bill['bill_id']))
                        action['related_entities'].remove(entity)
        if found:
            pass
            # import ipdb;ipdb.set_trace()





if __name__ == '__main__':
    main()