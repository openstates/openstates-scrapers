import pdb
import re
import os
import cookielib
import operator
import itertools
import contextlib
import logging
import datetime
import time
import hashlib
from os.path import join, dirname, abspath
from functools import partial
from collections import namedtuple, defaultdict
from operator import itemgetter, methodcaller

import nltk
import requests
import feedparser

from billy.models import db
from billy.utils import metadata
from billy.conf import settings


def trie_add(trie, seq_value_2_tuples, terminus=0):
    '''Given a trie (or rather, a dict), add the match terms into the
    trie.
    '''
    for seq, value in seq_value_2_tuples:

        this = trie
        w_len = len(seq) - 1
        for i, c in enumerate(seq):
            
            if c in ', ':
                continue
        
            try:
                this = this[c]
            except KeyError:
                this[c] = {}
                this = this[c]

            if i == w_len:
                this[terminus] = value
                
    return trie


class PseudoMatch(object):
    '''A fake match object that provides the same basic interface
    as _sre.SRE_Match.'''

    def __init__(self, group, start, end):
        self._group = group
        self._start = start
        self._end = end

    def group(self):
        return self._group

    def start(self):
        return self._start

    def end(self):
        return self._end

    def _tuple(self):
        return (self._group, self._start, self._end)

    def __repr__(self):
        return 'PseudoMatch(group=%r, start=%r, end=%r)' % self._tuple()


def trie_scan(trie, s,
         _match=PseudoMatch,
         second=itemgetter(1)):
    '''
    Finds all matches for `s` in trie.
    '''

    res = []
    match = []

    this = trie
    in_match = False

    for i, c in enumerate(s):

        if c in ",. '&[]":   
            if in_match:
                match.append((i, c))
            continue
            
        if c in this:
            this = this[c]
            match.append((i, c))
            in_match = True
            if 0 in this:
                _matchobj = _match(group=''.join(map(second, match)),
                                   start=match[0][0], end=match[-1][0])
                res.append([_matchobj] + this[0])

        else:
            in_match = False
            if match:
                match = []

            this = trie
            if c in this:
                this = this[c]
                match.append((i, c))
                in_match = True

    # Remove any matches that are enclosed in bigger matches.
    prev = None
    for tpl in reversed(res):
        match, _, _ = tpl
        start, end = match.start, match.end

        if prev:
            a = prev._start <= match._start
            b = match._end <= prev._end
            c = match._group in prev._group
            if a and b and c:
                res.remove(tpl)

        prev = match
        
    return res

@contextlib.contextmanager
def cd(dir_):
    '''Temporarily change dirs to minimize os.path.join biolerplate.'''
    cwd = os.getcwd()
    os.chdir(dir_)
    yield
    os.chdir(cwd)


def cat_product(s_list1, s_list2):
    '''Given two lists of strings, take the cartesian product
    of the lists and concat each resulting 2-tuple.'''
    prod = itertools.product(s_list1, s_list2)
    return map(partial(apply, operator.add), prod)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
def new_feed_id(entry, cache={}):
    '''Generate an entry id using the hash value of the title and link.
    Pad the number to 
    '''
    s = entry['title'] + entry['link']
    _id = entry['state'].upper() + 'F' + str(abs(hash(s))).zfill(21)
    return _id

PATH = dirname(abspath(__file__))
DATA = settings.BILLY_DATA_DIR


class Meta(type):

    _classes = set()

    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        meta._classes.add(cls)
        return cls

    @classmethod
    def classes(cls):
        return cls._classes - set([Base])


class Base(object):
    __metaclass__ = Meta

    def __init__(self):

        self.abbr = self.__class__.__name__.lower()

        logger = logging.getLogger(self.abbr)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        self.logger = logger

    @property
    def trie(self):
        try:
            return self._trie
        except AttributeError:
            return self._build_trie()

    def extract_bill(self, m):
        '''Given a match object m, return the _id of the related bill. 
        '''

    def extract_committee(self, m):
        pass

    def extract_legislator(self, m):
        pass

    def _build_trie(self):
        '''Interpolate values from this state's mongo records
        into the trie_terms strings. Create a new list of formatted
        strings to use in building the trie, then build.
        '''
        trie = {}
        trie_terms = self.trie_terms
        abbr = self.__class__.__name__.lower()

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


    def _scan_feed(self, feed):

        try:
            self.logger.info('- scanning %s' % feed['feed']['links'][0]['href'])
        except KeyError:
            self.logger.info('- scanning feed with no link provided, grrr...')
        
        for entry in feed['entries']:

            # Search the trie.
            matches = []
            link = entry['link']
            try:
                summary = nltk.clean_html(entry['summary'])
            except KeyError:
                # This entry has no summary. Skip.
                continue
            matches += trie_scan(self.trie, summary)

            # Search the regexes.
            for collection_name, rgxs in self.rgxs.items():
                for r in rgxs:
                    for m in re.finditer(r, summary):
                        matchobj = PseudoMatch(m.group(), m.start(), m.end())
                        matches.append([matchobj, collection_name])

            yield entry, matches

    def _process_feed(self, feed):
        abbr = self.abbr
        feed_entries = db.feed_entries
        third = itemgetter(2)

        # Find matching entities in the feed.
        for entry, matches in self._scan_feed(feed):                    
            matches = self._extract_entities(matches)

            ids = map(third, matches)
            strings = [m.group() for m, _, _ in matches]
            assert len(ids) == len(strings)

            # Add references and save in mongo.
            
            entry['state'] = abbr # list probably wiser
            entry['entity_ids'] = ids or None
            entry['entity_strings'] = strings or None
            entry['save_time'] = datetime.datetime.utcnow()
            entry['_id'] = new_feed_id(entry)
            entry['_type'] = 'feedentry'

            entry['summary'] = nltk.clean_html(entry['summary'])
            try:
                entry['summary_detail']['value'] = nltk.clean_html(
                    entry['summary_detail']['value'])
            except KeyError:
                pass

            # Patch the entry object to get rid of struct_time.
            for k, v in entry.items():
                if isinstance(v, time.struct_time):
                    t = time.mktime(entry[k])
                    dt = datetime.datetime.fromtimestamp(t)
                    entry[k] = dt
            
            try:
                feed_entries.save(entry)
            except:
                import pdb;pdb.set_trace()
            msg = 'Found %d related entities in %r'
            self.logger.info(msg % (len(ids), entry['title']))


    def process_all_feeds(self):
        '''Note to self...possible problems with entries getting 
        overwritten?
        '''
        abbr = self.abbr
        STATE_DATA = join(DATA, abbr, 'feeds')
        STATE_DATA_RAW = join(STATE_DATA, 'raw')
        _process_feed = self._process_feed

        with cd(STATE_DATA_RAW):
            for fn in os.listdir('.'):
                with open(fn) as f:
                    feed = feedparser.parse(f.read())
                    _process_feed(feed)


    def _extract_entities(self, matches):

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


class CA(Base):

    trie_terms = {
        'legislators': cat_product(

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
             u'Chairman',
             u'Chairwoman',
             u'Chairperson',], 

            [u' {legislator[last_name]}',
             u' {legislator[full_name]}'])

            + [u'{legislator[full_name]}']

         ,

        'bills': [ 
            ('bill_id', lambda s: s.upper().replace('.', ''))
            ]

        }

    rgxs = {
        'bills': [
            '(?:%s) ?\d[\w-]*' % '|'.join([
                'AB', 'ACR', 'AJR', 'SB', 'SCR', 'SJR'])
            ],

        'committees': [
            '(?:Assembly|Senate).{,200}?Committee',
            ]

    }


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
        ch = committee['chamber']
        if ch != 'joint':
            chamber_name = metadata('ca')[ch + '_chamber_name']
        else:
            chamber_name = 'Joint'

        # Arts
        raw = re.sub(r'(Standing|Joint|Select) Committee on ', '', name)
        raw = re.sub(r'\s+Committee$', '', raw)

        # Committee on Arts
        committee_on_1 = 'Committee on ' + raw

        # Arts Committee
        short = raw + ' Committee'
        
        # Assembly Arts Committee
        if not short.startswith(chamber_name):
            cow = chamber_name + ' ' + short
        else:
            cow = short

        # Assembly Committee on Arts
        committee_on_2 = ch + ' ' + committee_on_1

        # Exclude phrases less than two words in length.
        return set(filter(lambda s: ' ' in s,
                   [name, committee_on_1, committee_on_2, raw, short, cow]))


class IL(Base):

    trie_terms = {
        'legislators': cat_product(

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
             u'Representative'], 

            [u' {legislator[last_name]}',
             u' {legislator[full_name]}']),

        'bills': [ 
            ('bill_id', lambda s: s.upper().replace('.', ''))
            ]

        }

    rgxs = {
        'bills': [
            '(?:%s) ?\d[\w-]*' % '|'.join([
                'B', 'R', 'JR', 'JRCA',])
            ],

        'committees': [
            '(?:House of Representatives|House|Senate).{,200}?Committee',
            ]

    }


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
        ch = committee['chamber']
        if ch != 'joint':
            chamber_name = metadata('ca')[ch + '_chamber_name']
        else:
            chamber_name = 'Joint'

        # Arts
        raw = re.sub(r'(Standing|Joint|Select) Committee on ', '', name)
        raw = re.sub(r'\s+Committee$', '', raw)

        # Committee on Arts
        committee_on = 'Committee on ' + raw

        # Arts Committee
        short = raw + ' Committee'
        
        if not short.startswith(chamber_name):
            cow = chamber_name + ' ' + short
        else:
            cow = short

        # Exclude phrases less than two words in length.
        return set(filter(lambda s: ' ' in s,
                   [name, committee_on, raw, short, cow]))


class TX(Base):

    trie_terms = {
        'legislators': cat_product(

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
             u'Representative'], 

            [u' {legislator[last_name]}',
             u' {legislator[full_name]}']),

        'bills': [ 
            ('bill_id', lambda s: s.upper().replace('.', ''))
            ]

        }

    rgxs = {
        'bills': [
            '(?:%s) ?\d[\w-]*' % '|'.join([
                "SB", "HB", "HC", "HJ", "SC", "SJ",])
            ],

        'committees': [
            '(?:House of Representatives|House|Senate).{,200}?Committee',
            ]

    }


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
        ch = committee['chamber']
        if ch != 'joint':
            chamber_name = metadata('ca')[ch + '_chamber_name']
        else:
            chamber_name = 'Joint'

        # Arts
        raw = re.sub(r'(Standing|Joint|Select) Committee on ', '', name)
        raw = re.sub(r'\s+Committee$', '', raw)

        # Committee on Arts
        committee_on = 'Committee on ' + raw

        # Arts Committee
        short = raw + ' Committee'
        
        if not short.startswith(chamber_name):
            cow = chamber_name + ' ' + short
        else:
            cow = short

        # Exclude phrases less than two words in length.
        return set(filter(lambda s: ' ' in s,
                   [name, committee_on, raw, short, cow]))




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
    
    # appr = db.committees.find_one(u'CAC000084')
    # ca = CA()
    # s = '''e speakers at Wednesday mornings Assembly hearing on health care district. Assembly Committee on Accountability and Administrative Review Chairman Roger Dickinson, D-S'''
    # cow = trie_scan(ca.trie, s)
    # print cow
    # import pdb;pdb.set_trace()


    db.feed_entries.remove()
    for cls in Meta.classes():# & set([CA]):
        inst = cls()
        inst.process_all_feeds()

    # ca = CA()
    # ca._build_trie()
    # ma = []
    # ca.build()
    # x = ca.relevant.values()
    # bad = []
    # for y in itertools.chain.from_iterable(x):
    #     if y[-1] is None:
    #         print y
    #         bad.append(y)
    # comm = [y for y in itertools.chain.from_iterable(x) if y[1] == 'committees']
    # for y in itertools.chain.from_iterable(x):
    #     if y[1] == 'committees':
    #         print y
    # import pdb;pdb.set_trace()