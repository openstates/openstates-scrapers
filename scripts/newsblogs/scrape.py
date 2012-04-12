import pdb
import re
from os.path import join, dirname, abspath
import cookielib
import operator
from operator import methodcaller
import itertools
from functools import partial

import nltk
import requests
import feedparser

from billy.models import db
from billy.utils import metadata

import pdb
from collections import namedtuple, defaultdict
from operator import itemgetter
from operator import methodcaller 

def trie_add(trie, terms, terminus=0):
    '''Given a trie (or rather, a dict), add the match terms into the
    trie.
    '''
    for s in terms:
        
        this = trie
        s_len = len(s) - 1
        for i, c in enumerate(s):
            
            if c in ', ':
                continue
        
            try:
                this = this[c]
            except KeyError:
                this[c] = {}
                this = this[c]

            if i == s_len:
                this[terminus] = None
                
    return trie


def trie_scan(trie, s, 
         preprocessors=[methodcaller('lower')],
         _match=namedtuple('Match', 'text start end data'),
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
                res.append(_match(text=''.join(map(second, match)),
                                  start=match[0][0], end=match[-1][0],
                                  data=this[0]))

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
    for match in reversed(res):

        start, end = match.start, match.end

        if prev:
            a = prev.start <= match.start
            b = match.end <= prev.end
            c = match.text in prev.text
            if a and b and c:
                res.remove(match)

        prev = match
        
    return res

# ----------------------------------------------------------------------------
# Fetch the feeds.

feeds = '''
    http://www.sfgate.com/rss/feeds/news_politics.xml
    http://feeds.feedburner.com/CaliforniaPolitics
    http://blogs.kqed.org/capitalnotes/feed/
    http://www.sfgate.com/rss/feeds/blogs/sfgate/nov05election/index_rss2.xml
    http://www.capitolbasement.com/rss.php?_c=10h5g5p944kp5pw
    http://www.laobserved.com/index.xml
    http://www.californiascapitol.com/blog/feed/rss/
    http://www.ocregister.com/sections/rss/
    http://www.newwestnotes.com/feed/
    http://www.ibabuzz.com/politics/feed/
    http://www.ocregister.com/common/rss/rss.php?catID=18805
    http://www.camajorityreport.com/index.php?theme=rss
    http://feeds.feedburner.com/CaliticsFeed
    http://www.camajorityreport.com/index.php?theme=rss
    http://feeds.feedburner.com/EnvironmentalUpdates
    http://www.flashreport.org/blog/?feed=rss
    http://www.ocblog.net/feed/
    http://capoliticalnews.com/feed/
    http://rosereport.org/index.php?option=com_easyblog&view=categories&format=feed&type=rss&id=57&Itemid=198
    http://kimalex.blogspot.com/feeds/posts/default
    http://californiacitynews.typepad.com/californiacitynewsorg/atom.xml
    http://feeds.feedburner.com/blogspot/uqpFc
    http://inbox.berkeley.edu/feed/
    http://electionlawblog.org/?feed=rss2
    http://www.cawrecycles.org/taxonomy/term/10/0/feed
    http://www.sacbee.com/politics/index.rss
    http://www.sacbee.com/state/index.rss
    http://www.sacbee.com/gov2010/index.rss
    http://www.sacbee.com/static/weblogs/capitolalertlatest/atom.xml
    http://www.sacbee.com/stateworker/index.rss
    http://www.sacbee.com/static/weblogs/the_state_worker/atom.xml
    http://www.sacbee.com/static/weblogs/weed-wars/atom.xml
    http://www.sacbee.com/sierrawarming/index.rss
    http://www.sacbee.com/walters/index.rss
    '''.split()

PATH = dirname(abspath(__file__))

request_defaults = {
    'proxies': {"http": "localhost:8001"},
    #'cookies': cookielib.LWPCookieJar(join(PATH, 'cookies.lwp')),
    'headers': {
        'Accept': ('text/html,application/xhtml+xml,application/'
                   'xml;q=0.9,*/*;q=0.8'),
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0.2) '
                       'Gecko/20100101 Firefox/10.0.2')
        },
    }

session = requests.Session(**request_defaults)
from requests import async

rs = [async.get(url, **request_defaults) for url in feeds]
responses = async.map(rs, size=4)

# _feeds = []
# for resp in responses:
#     text = resp.text
#     feed = feedparser.parse(text)
#     _feeds.append((url, feed))


# # ---------------------------------------------------------------------------
# # Build the trie.
# meta = metadata('ca')

# # legislature_name upper_chamber_name lower_chamber_name
# term_keys = [
#     'Assemblymember', 'Assembly Member', 'Assemblyman',
#     'Assemblywoman', 'Assembly person'
#     ]

# #terms = map(meta.get, term_keys)

# legs = list(db.legislators.find({'state': 'ca'}))
# coms = list(db.committees.find({'state': 'ca'}))

# hits = defaultdict(set)

# lowercase = methodcaller('lower')
# terms = set()

# term_to_id = {}

# # Matches include:
# # - Assembly Member Tony Strickland
# # - Assembly Member Strickland
# # - Assemblymember Strickland
# # - Assemblyman Strickland
# # - Assemblywoman Strickland
# # - Assemblyperson Strickland
# _terms = set()
# for leg in legs:
#     legid = leg['_id']
#     last = leg['last_name']
#     full = leg['full_name']
#     for t in term_keys:
#         _add_terms = [t + ' ' + last,
#                       t + ' ' + full,
#                       full]
#         for t in _add_terms:
#             _terms.add(t)
#             term_to_id[t] = ('legislator', legid)

# # for com in coms:
# #     _terms.add(com['committee'])
# #     if com['subcommittee']:
# #         _terms.add(com['subcommittee'])

# re_bills = '(?:%s) ?\d[\w-]*' % '|'.join(['AB', 'ACR', 'AJR', 'SB', 'SCR', 'SJR'])
# re_committees = '(?:Assembly|Senate).{,200}?Committee'

# trie = trie_add({}, _terms)

# for url, f in _feeds:
#     res = []
#     for e in f['entries']:
#         text = nltk.clean_html(e['summary'])
#         link = e['link']

#         # Legislators.
#         matches = trie_scan(trie, text)
#         if matches:
#             hits[link] |= set(matches)

#         # Bills.
#         matches = set(re.findall(re_bills, text))
#         if matches:
#             hits[link] |= set(matches)

#             for m in matches:
#                 x = db.bills.find_one({'state': 'ca', 'bill_id': m}, {'_id': 1})
#                 if x:
#                     term_to_id[m] = ('bill', x['_id'])

#         # Committees.
#         matches = re.findall(re_committees, text)
#         if matches:
#             hits[link] |= set(matches)

#             for m in matches:
#                 #x = db.committees.find_one({'state': 'ca', 'bill_id': m}, {'_id': 1})
#                 #if x:
#                 term_to_id[m] = ('', 'foo')

# import pprint
# pprint.pprint(hits)
# pdb.set_trace()

# for link, kw in hits.items():
#     print link, kw


class Meta(type):
    classes = [] 
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        meta.classes.append(cls)
        return cls

class Base(object):
    __metaclass__ = Meta

    def related_bill(self, m):
        '''Given a match object m, return the _id of the related bill. 
        '''
        pass

    def related_committee(self, m):
        pass

    def related_legislator(self, m):
        pass

    def _compile(self):
        '''Interpoolate values from this state's mongo records
        into the trie_terms strings. Create a new list of formatted
        strings to use in building the trie.
        '''
        compiled_terms = [] 
        trie_terms = self.trie_terms
        abbr = self.__class__.__name__.lower()
        for collection_name in trie_terms:
            collection = getattr(db, collection_name)
            cursor = collection.find({'state': abbr})
            for record in cursor:
                k = collection_name.rstrip('s')
                vals = {k: record}
                for term in trie_terms[collection_name]:
                    compiled_terms.append(term.format(**vals))
        self.trie = trie_add({}, compiled_terms)
        self.compiled_terms = compiled_terms
        return compiled_terms


    def _process_feed(self, resp):

        matches = []
        feed = feedparser.parse(resp.text)
        for e in feed['entries']:
            link = e['link']
            summary = nltk.clean_html(e['summary'])
            matches += trie_scan(self.trie, summary)
        return matches
        

def cat_product(s_list1, s_list2):
    '''Given two lists of strings, take the cartesian product
    of the lists and concat east resulting 2-tuple.'''
    prod = itertools.product(s_list1, s_list2)
    return map(partial(apply, operator.add), prod)

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
             u'Assembly person'], 

            [u' {legislator[last_name]}',
             u' {legislator[full_name]}'])}

    rgxs = {
        'bills': [
            '(?:%s) ?\d[\w-]*' % '|'.join([
                'AB', 'ACR', 'AJR', 'SB', 'SCR', 'SJR'])
            ],

        'committees': [
            '(?:Assembly|Senate).{,200}?Committee',
            ]

    }

'''
To-do:
Make trie-scan return a pseudo-match object that has same
interface as re.matchobjects. 

Handle A.B. 200 variations for bills.

Tune committee regexes.

Investigate other jargon and buzz phrase usage i.e.:
 - speaker of the house
 - committee chair
'''
if __name__ == '__main__':
    ca = CA()
    ca._compile()
    ma = []
    for r in responses:
        ma += ca._process_feed(r)
    import pdb;pdb.set_trace()