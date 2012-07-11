import operator
import difflib
import logging
from collections import defaultdict
from cStringIO import StringIO
import csv
import codecs

from billy.models import db, Metadata

# Logging config
logger = logging.getLogger('match-test')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class State(object):

    def __init__(self, abbr, chamber, cutoff=0.6):
        self.abbr = abbr
        self.chamber = chamber
        self.cutoff = cutoff
        self.metadata = Metadata.get_object(abbr)

    @property
    def matched(self):
        return self.name_data[0]

    @property
    def unmatched(self):
        return self.name_data[1]

    @property
    def name_to_ids(self):
        return self.name_data[2]

    @property
    def name_data(self):
        '''Get all unmatched_ids from committees, votes.
        '''
        # Store all the name variations used for each leg_id.

        try:
            return self._matched, self._unmatched, self._name_to_ids
        except AttributeError:
            pass
        matched = defaultdict(set)
        unmatched = set()
        name_to_ids = defaultdict(set)

        logger.debug('Getting all voter names...')
        for bill in self.metadata.bills({'chamber': self.chamber}):
            for vote in bill.votes_manager():
                for type_ in ['yes_votes', 'no_votes', 'other_votes']:
                    for voter in vote[type_]:
                        if voter['leg_id'] is not None:
                            matched[voter['leg_id']].add(voter['name'])
                        else:
                            unmatched.add(voter['name'])

        msg = 'Found %d unmatched, %d matched.'
        logger.debug(msg % (len(unmatched), len(matched)))

        logger.debug('Getting all committee member names.')
        for committee in self.metadata.committees({'chamber': self.chamber}):
            for member in committee['members']:
                if member['leg_id'] is not None:
                            matched[member['leg_id']].add(member['name'])
                else:
                    unmatched.add(member['name'])
        msg = 'Found %d unmatched, %d matched.'
        logger.debug(msg % (len(unmatched), len(matched)))

        logger.debug('Getting all legislator names')
        for legislator in self.metadata.legislators(
                        {'active': True, 'chamber': self.chamber}):
            _id = legislator['leg_id']
            name_to_ids[legislator['full_name'].lower()].add(_id)
            name_to_ids[legislator['last_name'].lower()].add(_id)
            name_to_ids[legislator['_scraped_name'].lower()].add(_id)

        self._matched = matched
        self._unmatched = list(unmatched)
        self._name_to_ids = name_to_ids
        return matched, unmatched, name_to_ids

    def get_name_id(self, namestring):
        matches = difflib.get_close_matches(namestring.lower(),
                                            self.name_to_ids,
                                            cutoff=self.cutoff)
        if matches:
            name = matches[0]
            return self.name_to_ids[name], name, namestring
        else:
            return None, None, namestring

    def csv_rows(self):
        buf = StringIO()
        writer = UnicodeWriter(buf)

        # Cache of data already added.
        added = set()
        for namestring in state.unmatched:
            skip = False
            ids, name, namestring = self.get_name_id(namestring)
            if not ids:
                msg = 'No matches found for %r'
                logger.info(msg % namestring)
                continue

            # Potential prob if there are more than 1 id.
            if 1 < len(ids):
                msg = 'There were %d possible ids for %r'
                logger.warning(msg % (len(ids), namestring))
                legs = db.legislators.find({'active': True, '_id': {'$in': list(ids)}})
                for leg in legs:
                    logger.warning('  -- %r %r' % (leg['_scraped_name'], leg['_id']))
                skip = True

            if skip:
                continue

            for _id in ids:
                legislator = db.legislators.find_one(_id)
                for session in map(operator.itemgetter('term'),
                                   legislator['roles']):
                    vals = [session, legislator['chamber'],
                            namestring, _id]
                    if tuple(vals) in added:
                        continue
                    writer.writerow(vals)
                    msg = 'Wrote row associating %r with %r, %r'
                    logger.debug(msg % (namestring, _id,
                                        legislator['full_name']))
                    added.add(tuple(vals))

        return buf.getvalue()


if __name__ == '__main__':
    import sys
    abbr = sys.argv[1]
    chamber = sys.argv[2]
    try:
        cutoff = float(sys.argv[3])
    except IndexError:
        cutoff = 0.6
    state = State(abbr, chamber)
    print state.csv_rows()
    

