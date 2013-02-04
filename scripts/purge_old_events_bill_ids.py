import sys
import re
from collections import defaultdict, Counter

from billy.core import db
from billy.core import settings
from billy.core import logging
from billy.utils import fix_bill_id


def main():

    abbrs = sys.argv[1:] or [x['abbreviation'] for x in db.metadata.find()]
    logger = logging.getLogger('billy.purge_committee_ids')
    logger.setLevel(logging.INFO)
    tally = defaultdict(Counter)

    for abbr in abbrs:
        abbr_tally = tally['abbr']
        spec = {
            settings.LEVEL_FIELD: abbr,
            'related_bills': {'$exists': True, '$ne': []},
            }
        for event in db.events.find(spec):
            fixed = []
            for bill in event['related_bills']:

                bill_id = bill.get('bill_id')
                if bill_id is not None:

                    # If "bill_id" is a big id, rename it.
                    if re.match(r'[A-Z]{2}B\d{8}', bill_id):
                        _id = bill.pop('bill_id')
                        bill['id'] = _id
                        logger.info('Renamed "bill_id" to "id"')
                        abbr_tally['bill_id --> id'] += 1

                    # If it's something else, do fix_bill_id to
                    # fix screwed up old ids.
                    else:
                        bill['bill_id'] = fix_bill_id(bill['bill_id'])
                        logger.info('Fixed an un-fixed bill_id')
                        abbr_tally['fix_bill_id'] += 1

                    fixed = True

                if '_scraped_bill_id' in bill:
                    bill_id = fix_bill_id(bill.pop('_scraped_bill_id'))
                    bill['bill_id'] = bill_id
                    logger.info('Renamed "_scraped_bill_id" to "bill_id"')
                    abbr_tally['_scraped_bill_id --> bill_id'] += 1

                    fixed = True

            if fixed:
                msg = 'Updating related_bills on event %r.'
                logger.debug(msg % event['_id'])
                db.events.save(event)

        logger.info(abbr)
        # for item in abbr_tally.items():
        #     logger.info('%s %d' % item)
        # import ipdb;ipdb.set_trace()


if __name__ == '__main__':
    main()
