import re
import os
import json
import hashlib
import logging
import datetime
import urlparse
import collections
from os.path import join, dirname, abspath
from operator import itemgetter

import pymongo

from billy.core import db
from billy.utils import metadata
from billy.core import settings

from trie_utils import Trie, trie_add, trie_scan
from utils import cd, cartcat, clean_html



# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------

host = settings.MONGO_HOST
port = settings.MONGO_PORT

conn = pymongo.Connection(host, port)
feed_db = conn.newsblogs


class BogusEntry(Exception):
    '''Raised when an entry lacks a required attribute, like 'link'.'''


def new_entry_id(entry, cache={}):
    '''Generate an entry id using the hash value of the title and link.
    '''
    s = (entry['link'] + entry['title']).encode('ascii', 'ignore')
    return hashlib.md5(s).hexdigest()


PATH = dirname(abspath(__file__))
DATA = settings.BILLY_DATA_DIR


class Extractor(object):

    trie_terms = {
        'legislators': cartcat(

            [u'Senator',
             u'Senate member',
             u'Senate Member',
             u'Assemblymember',
             u'Assembly Member',
             u'Assembly member',
             u'Assemblyman',
             u'Assemblywoman',
             u'Assembly person',
             u'Assemblymember',
             u'Assembly Member',
             u'Assembly member',
             u'Assemblyman',
             u'Assemblywoman',
             u'Assembly person',
             u'Representative',
             u'Rep.',
             u'Sen.',
             u'Council member',
             u'Councilman',
             u'Councilwoman',
             u'Councilperson'],

            [u' {legislator[last_name]}',
             u' {legislator[full_name]}'])

            + [u' {legislator[first_name]} {legislator[last_name]}'],

        'bills': [
            ('bill_id', lambda s: s.upper().replace('.', ''))
            ]

        }

    def __init__(self, abbr):
        self.entrycount = 0
        self.abbr = abbr
        self._assemble_ban_data()

        logger = logging.getLogger('billu.extractor.' + abbr)
        self.logger = logger

    @property
    def metadata(self):
        return metadata(self.abbr)

    def extract_bill(self, m, collection=db.bills, cache={}):
        '''Given a match object m, return the _id of the related bill.
        '''
        def squish(bill_id):
            bill_id = ''.join(bill_id.split())
            bill_id = bill_id.upper().replace('.', '')
            return bill_id

        bill_id = squish(m.group())

        try:
            ids = cache['ids']
        except KeyError:
            # Get a list of (bill_id, _id) tuples like ('SJC23', 'CAB000123')
            ids = collection.find({'state': self.abbr}, {'bill_id': 1})
            ids = dict((squish(r['bill_id']), r['_id']) for r in ids)

            # Cache it in the method.
            cache['ids'] = ids

        if bill_id in ids:
            return ids[bill_id]

    def committee_variations(self, committee):
        '''Compute likely variations for a committee
        Standing Committee on Rules
         - Rules Committee
         - Committee on Rules
         - Senate Rules
         - Senate Rules Committee
         - Rules (useless)
        '''
        name = committee['committee']
        chamber = committee['chamber']
        if chamber != 'joint':
            chamber_name = self.metadata['chambers'][chamber]['name']
        else:
            chamber_name = 'Joint'

        # Arts
        raw = re.sub(r'(Standing|Joint|Select) Committee on ', '', name)
        raw = re.sub(r'\s+Committee$', '', raw)

        # Committee on Arts
        committee_on_1 = 'Committee on ' + raw

        # Arts Committee
        short1 = raw + ' Committee'

        # Assembly Arts Committee
        if not short1.startswith(chamber_name):
            short2 = chamber_name + ' ' + short1
        else:
            short2 = short1

        # Assembly Committee on Arts
        committee_on_2 = chamber_name + ' ' + committee_on_1

        phrases = [name, committee_on_1, committee_on_2, short1, short2]

        # "select Committee weirdness"
        phrases += ['Select ' + committee_on_1]

        # Adjust for ampersand usage like "Senate Public Employment &
        # Retirement Committee"
        phrases += [p.replace(' and ', ' & ') for p in phrases]

        # Exclude phrases less than two words in length.
        return set(filter(lambda s: ' ' in s, phrases))

    @property
    def trie(self):
        try:
            return self._trie
        except AttributeError:
            return self.build_trie()

    def build_trie(self):
        '''Interpolate values from this state's mongo records
        into the trie_terms strings. Create a new list of formatted
        strings to use in building the trie, then build.
        '''
        trie = Trie()
        trie_terms = self.trie_terms
        abbr = self.abbr

        for collection_name in trie_terms:
            trie_data = []
            collection = getattr(db, collection_name)
            cursor = collection.find({'state': abbr})
            self.logger.info('compiling %d %r trie term values' % (
                cursor.count(), collection_name))

            for record in cursor:
                k = collection_name.rstrip('s')
                vals = {k: record}

                for term in trie_terms[collection_name]:

                    if isinstance(term, basestring):
                        trie_add_args = (term.format(**vals),
                                         [collection_name, record['_id']])
                        trie_data.append(trie_add_args)

                    elif isinstance(term, tuple):
                        k, func = term
                        trie_add_args = (func(record[k]),
                                         [collection_name, record['_id']])
                        trie_data.append(trie_add_args)

            self.logger.info('adding %d %s terms to the trie' % \
                (len(trie_data), collection_name))

            trie = trie_add(trie, trie_data)

        if hasattr(self, 'committee_variations'):

            committee_variations = self.committee_variations
            trie_data = []
            records = db.committees.find({'state': abbr},
                                         {'committee': 1, 'subcommittee': 1,
                                          'chamber': 1})
            self.logger.info('Computing name variations for %d records' % \
                                                            records.count())
            for c in records:
                for variation in committee_variations(c):
                    trie_add_args = (variation, ['committees', c['_id']])
                    trie_data.append(trie_add_args)

        self.logger.info('adding %d \'committees\' terms to the trie' % \
                                                            len(trie_data))

        trie = trie_add(trie, trie_data)
        self._trie = trie
        return trie

    def scan_feed(self, entries):

        for entry in entries:
            self.entrycount += 1
            yield self.scan_entry(entry)

    def scan_entry(self, entry):
        '''Test an entry against the trie to see if any entities
        are found.
        '''
        # Search the trie.
        matches = []
        try:
            summary = clean_html(entry['summary'])
        except KeyError:
            # This entry has no summary. Skip.
            return entry, []
        matches += trie_scan(self.trie, summary)

        return entry, matches

    def process_entry(self, entry):
        '''Given an entry, add a mongo id and other top-level
        attributes, then run it through scan_feed to recognize
        any entities mentioned.
        '''
        abbr = self.abbr
        third = itemgetter(2)

        entry, matches = self.scan_entry(entry)
        matches = self.extract_entities(matches)

        ids = map(third, matches)
        strings = [m.group() for m, _, _ in matches]
        assert len(ids) == len(strings)

        # Add references and save in mongo.
        entry['state'] = abbr  # list probably wiser
        entry['entity_ids'] = ids or []
        entry['entity_strings'] = strings or []
        entry['save_time'] = datetime.datetime.utcnow()

        try:
            entry['_id'] = new_entry_id(entry)
        except BogusEntry:
            # This entry appears to be malformed somehow. Skip.
            msg = 'Skipping malformed feed: %s'
            msg = msg % repr(entry)[:100] + '...'
            self.logger.info(msg)
            return

        entry['_type'] = 'feedentry'

        try:
            entry['summary'] = clean_html(entry['summary'])
        except KeyError:
            return
        try:
            entry['summary_detail']['value'] = clean_html(
                entry['summary_detail']['value'])
        except KeyError:
            pass

        # Kill any keys that contain dots.
        entry = dict((k, v) for (k, v) in entry.items() if '.' not in k)

        # Bail if the feed contains any banned key-value pairs.
        entry_set = self._dictitems_to_set(entry)
        for keyval_set in self._banned_keyvals:
            if entry_set & keyval_set:
                msg = 'Skipped story containing banned key values: %r'
                self.logger.info(msg % keyval_set)
                return

        # Skip any entries that are missing required keys:
        required = set('summary source host link published_parsed'.split())
        if required not in set(entry):
            if 'links' not in entry:
                msg = 'Skipped story lacking required keys: %r'
                self.logger.info(msg % (required - set(entry)))
                return
            else:
                source = entry['links'][-1].get('href')
                if source:
                    host = urlparse.urlparse(entry['links'][0]['href']).netloc
                    entry['source'] = source
                    entry['host'] = host
                else:
                    msg = 'Skipped story lacking required keys: %r'
                    self.logger.info(msg % (required - set(entry)))
                    return

        # Save
        msg = 'Found %d related entities in %r'
        if ids:
            self.logger.info(msg % (len(ids), entry['title']))
        else:
            self.logger.debug(msg % (len(ids), entry['title']))
        return entry
        # feed_db.entries.save(entry)

    def process_feed(self, entries):
        # Find matching entities in the feed.
        for entry, matches in self.scan_feed(entries):
            self.process_entry(entry, matches)

    def process_all_feeds(self):
        '''Note to self...possible problems with entries getting
        overwritten?
        '''
        abbr = self.abbr
        STATE_DATA = join(DATA, abbr, 'feeds')
        STATE_DATA_RAW = join(STATE_DATA, 'raw')
        _process_feed = self.process_feed

        with cd(STATE_DATA_RAW):
            for fn in os.listdir('.'):
                with open(fn) as f:
                    entries = json.load(f)
                    _process_feed(entries)

    def extract_entities(self, matches):

        funcs = {}
        for collection_name, method in (('bills', 'extract_bill'),
                                        ('legislators', 'extract_legislator'),
                                        ('committees', 'extract_committees')):

            try:
                funcs[collection_name] = getattr(self, method)
            except AttributeError:
                pass

        processed = []
        for m in matches:

            if len(m) == 2:
                match, collection_name = m
                extractor = funcs.get(collection_name)
                if extractor:
                    _id = extractor(match)
                    processed.append(m + [_id])
            else:
                processed.append(m)

        return processed

    def _assemble_ban_data(self):
        '''Go through this state's file in newblogs/skip, parse each line
        into a JSON object, and store them in the Extractor.
        '''
        here = dirname(abspath(__file__))
        skipfile = join(here,  'skip', '%s.txt' % self.abbr)
        banned_keyvals = []
        try:
            with open(skipfile) as f:
                for line in filter(None, f):
                    data = json.loads(line)
                    data = self._dictitems_to_set(data)
                    banned_keyvals.append(set(data))
        except IOError:
            pass
        self._banned_keyvals = banned_keyvals

    def _dictitems_to_set(self, dict_):
        return set((k, v) for (k, v) in dict_.items()
                   if isinstance(v, collections.Hashable))

'''
To-do:
DONE - Make trie-scan return a pseudo-match object that has same
interface as re.matchobjects.

DONE - Handle A.B. 200 variations for bills.

DONE-ish... Tune committee regexes.

- Add chambers the entry is relevant to so we can query by state
and chamber in addition to entity.

Investigate other jargon and buzz phrase usage i.e.:
 - speaker of the house
 - committee chair

'''

if __name__ == '__main__':

    import sys
    from os.path import dirname, abspath

    PATH = dirname(abspath(__file__))

    if sys.argv[1:]:
        states = sys.argv[1:]
    else:
        filenames = os.listdir(join(PATH, 'urls'))
        filenames = [s.replace('.txt', '') for s in filenames]
        states = filter(lambda s: '~' not in s, filenames)

    stats = {}
    for abbr in states:
        ex = Extractor(abbr)
        ex.process_all_feeds()
        stats[ex.abbr] = ex.entrycount

    # logger = logging.getLogger('mysql-update')
    # logger.setLevel(logging.INFO)

    # ch = logging.StreamHandler()
    # formatter = logging.Formatter('%(asctime)s - %(message)s',
    #                               datefmt='%H:%M:%S')
    # ch.setFormatter(formatter)
    # logger.addHandler(ch)

    # for abbr, count in stats.items():
    #     logger.info('%s - scanned %d feed entries' % (abbr, count))
