import re
import json
import os
import operator
import functools
import collections
import htmlentitydefs
import urlparse
import itertools
import contextlib
import logging
import datetime
from os.path import join, dirname, abspath
from operator import itemgetter

import pymongo
from functools import partial

from billy.core import db
from billy.utils import metadata
from billy.core import settings


host = settings.MONGO_HOST
port = settings.MONGO_PORT

conn = pymongo.Connection(host, port)
feed_db = conn.newsblogs


class _CachedAttr(object):
    '''Computes attr value and caches it in the instance.'''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result


def unescape(text):
    '''Removes HTML or XML character references and entities from a text string.
    @param text The HTML (or XML) source text.
    @return The plain text, as a Unicode string, if necessary.
    '''
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


class Trie(dict):

    @_CachedAttr
    def finditer(self):
        return functools.partial(re.finditer, '|'.join(self))


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


def trie_add(trie, seq_value_2tuples, terminus=0):
    '''Given a trie (or rather, a dict), add the match terms into the
    trie.
    '''
    for seq, value in seq_value_2tuples:

        this = trie
        w_len = len(seq) - 1
        for i, c in enumerate(seq):

            if c in ",. '&[]":
                continue

            try:
                this = this[c]
            except KeyError:
                this[c] = {}
                this = this[c]

            if i == w_len:
                this[terminus] = value

    return trie


def trie_scan(trie, s,
         _match=PseudoMatch,
         second=itemgetter(1)):
    '''
    Finds all matches for `s` in `trie`.
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


# def trie_scan(trie, string, _match=PseudoMatch,
#               second=itemgetter(1)):

#     this = trie
#     match = []
#     spans = []

#     for matchobj in trie.finditer(string):

#         pos = matchobj.start()
#         this = trie
#         match = []

#         while True:

#             try:
#                 char = string[pos]
#             except IndexError:
#                 break

#             if char in ",. '&[]":
#                 match.append((pos, char))
#                 pos += 1
#                 continue

#             try:
#                 this = this[char]
#             except KeyError:
#                 break
#             else:
#                 match.append((pos, char))
#                 if 0 in this:
#                     start = matchobj.start()
#                     end = pos
#                     pseudo_match = _match(group=''.join(map(second, match)),
#                                           start=start, end=end)

#                     # Don't yeild a match if this match is contained in a
#                     # larger match.
#                     _break = False
#                     for _start, _end in spans:
#                         if (_start <= start) and (end <= _end):
#                             _break = True
#                     if _break:
#                         break

#                     spans.append((start, end))
#                     yield [pseudo_match] + this[0]
#                     break
#                 else:
#                     pos += 1


@contextlib.contextmanager
def cd(path):
    '''Creates the path if it doesn't exist'''
    old_dir = os.getcwd()
    try:
        os.makedirs(path)
    except OSError:
        pass
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


def cartcat(s_list1, s_list2):
    '''Given two lists of strings, take the cartesian product
    of the lists and concat each resulting 2-tuple.'''
    prod = itertools.product(s_list1, s_list2)
    return map(partial(apply, operator.add), prod)


def clean_html(html):
    """
    Remove HTML markup from the given string. Borrowed from nltk.
    """
    # First we remove inline JavaScript/CSS:
    cleaned = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html.strip())
    # Then we remove html comments. This has to be done before removing regular
    # tags since comments can contain '>' characters.
    cleaned = re.sub(r"(?s)<!--(.*?)-->[\n]?", "", cleaned)
    # Next we can remove the remaining tags:
    cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
    # Finally, we deal with whitespace
    cleaned = re.sub(r"&nbsp;", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    cleaned = re.sub(r"  ", " ", cleaned)
    return cleaned.strip()

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
class BogusEntry(Exception):
    '''Raised when an entry lacks a required attribute, like 'link'.'''


def new_feed_id(entry, cache={}):
    '''Generate an entry id using the hash value of the title and link.
    Pad the number to 21 digits.
    '''
    try:
        s = entry['title'] + entry['link']
    except KeyError:
        msg = 'Required key missing: %r'
        raise BogusEntry(msg % entry)

    hashval = hash(s)
    sign = ('A' if 0 < hashval else 'B')
    _id = entry['state'].upper() + 'F' + (str(hashval) + sign).zfill(21)
    return _id

PATH = dirname(abspath(__file__))
DATA = settings.BILLY_DATA_DIR


class Extractor(object):

    full_name = [u' {legislator[first_name]} {legislator[last_name]}']
    trie_terms = {
        'legislators': {
            'upper': cartcat(
                [u'Senator', u'Senate member', u'Senate Member', u'Sen.',
                 u'Council member', u'Councilman', u'Councilwoman',
                 u'Councilperson'],
                [u' {legislator[last_name]}', u' {legislator[full_name]}']
                ) + full_name,

            'lower': cartcat([
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
                u'Council member', u'Councilman',
                u'Councilwoman', u'Councilperson'],
                [u' {legislator[last_name]}', u' {legislator[full_name]}']
                ) + full_name,
                },

        'bills': [
            ('bill_id', lambda s: s.upper().replace('.', ''))
            ]

        }

    def __init__(self, abbr):
        self.entrycount = 0
        self.abbr = abbr
        self._assemble_ban_data()

        logger = logging.getLogger(abbr)
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
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
        ch = committee['chamber']
        if ch != 'joint':
            chamber_name = self.metadata['chambers'][ch]['name']
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

    def format_trie_term(self, term, vals, collection_name, record):
        if isinstance(term, basestring):
            trie_add_args = (term.format(**vals),
                             [collection_name, record['_id']])
            return trie_add_args

        elif isinstance(term, tuple):
            k, func = term
            trie_add_args = (func(record[k]),
                             [collection_name, record['_id']])
            return trie_add_args

    def build_trie(self):
        '''Interpolate values from this state's mongo records
        into the trie_terms strings. Create a new list of formatted
        strings to use in building the trie, then build.
        '''
        trie = Trie()
        trie_terms = self.trie_terms
        abbr = self.abbr

        for collection_name in trie_terms:
            spec = {'state': abbr}
            trie_data = []
            collection = getattr(db, collection_name)
            if collection_name == 'legislators':
                spec['active'] = True
            cursor = collection.find(spec)
            self.logger.info('compiling %d %r trie term values' % (
                cursor.count(), collection_name))

            for record in cursor:
                k = collection_name.rstrip('s')
                vals = {k: record}

                terms = trie_terms[collection_name]
                if collection_name == 'legislators':
                    # Skip lieutennant governors and other non-legislator actors
                    if 'chamber' not in record:
                        continue
                    else:
                        terms = terms[record['chamber']]

                for term in terms:
                    args = term, vals, collection_name, record
                    trie_data.append(self.format_trie_term(*args))

            self.logger.info('adding %d %s terms to the trie' %
                             (len(trie_data), collection_name))

            trie = trie_add(trie, trie_data)

        if hasattr(self, 'committee_variations'):

            committee_variations = self.committee_variations
            trie_data = []
            records = db.committees.find({'state': abbr},
                                         {'committee': 1, 'subcommittee': 1,
                                          'chamber': 1})
            self.logger.info('Computing name variations for %d records' %
                             records.count())
            for c in records:
                for variation in committee_variations(c):
                    trie_add_args = (variation, ['committees', c['_id']])
                    trie_data.append(trie_add_args)

        self.logger.info('adding %d \'committees\' terms to the trie' %
                         len(trie_data))

        trie = trie_add(trie, trie_data)
        self._trie = trie
        return trie

    def scan_feed(self, entries):

        for entry in entries:
            self.entrycount += 1

            # Search the trie.
            matches = []
            try:
                summary = clean_html(entry['summary'])
            except KeyError:
                # This entry has no summary. Skip.
                continue
            matches += trie_scan(self.trie, summary)

            yield entry, matches

    def process_feed(self, entries):
        abbr = self.abbr
        feed_entries = feed_db.entries
        third = itemgetter(2)

        # Find matching entities in the feed.
        for entry, matches in self.scan_feed(entries):
            matches = self.extract_entities(matches)

            ids = map(third, matches)
            strings = [m.group() for m, _, _ in matches]
            assert len(ids) == len(strings)

            # Add references and save in mongo.
            entry['state'] = abbr  # list probably wiser
            entry['entity_ids'] = ids or None
            entry['entity_strings'] = strings or None
            entry['save_time'] = datetime.datetime.utcnow()

            try:
                entry['_id'] = new_feed_id(entry)
            except BogusEntry:
                # This entry appears to be malformed somehow. Skip.
                msg = 'Skipping malformed feed: %s'
                msg = msg % repr(entry)[:100] + '...'
                self.logger.info(msg)
                continue

            entry['_type'] = 'feedentry'

            entry['summary'] = unescape(clean_html(entry['summary']))
            try:
                entry['summary_detail']['value'] = unescape(clean_html(
                    entry['summary_detail']['value']))
            except KeyError:
                pass

            entry['title'] = unescape(entry['title'])

            # Kill any keys that contain dots.
            entry = dict((k, v) for (k, v) in entry.items() if '.' not in k)

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
            feed_entries.save(entry)
            msg = 'Found %d related entities in %r'
            self.logger.info(msg % (len(ids), entry['title']))

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
    from os.path import dirname, abspath, join

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

    logger = logging.getLogger('newsblogs fetch')
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(message)s',
                                  datefmt='%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    for abbr, count in stats.items():
        logger.info('%s - scanned %d feed entries' % (abbr, count))
