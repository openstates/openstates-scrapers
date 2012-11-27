'''
The index is a mapping of work stems to lists of objects whose attributes
contain the strings. The results are type, object pairs.

Basic workflow to build the search index:

For each term--
  - reduce it to a set of words
  - subtract stopwords
  - stem each word and add the term's id to the search index
  - add the removed tail to another set corresponding to each stem.

If the result is not huge, expand the search index to include fragments
of stemmed words as well.
'''
import sys
import json
import collections
import itertools
import time
import datetime
import re
import nltk


class IndexBuilder(object):

    def __init__(self):
        self.stem2id = {}
        self.index = collections.defaultdict(lambda: set())
        self.tails = collections.defaultdict(lambda: set())
        self.stemmer = nltk.stem.porter.PorterStemmer()
        self.stopwords = set(nltk.corpus.stopwords.words('english'))
        self.stem_word = self.stemmer.stem_word
        self.f = lambda _s: len(_s) > 1
        self.new_id = itertools.count()
        self.objects = {}

    def get_stem_id(self, stem):

        # Get the stem's id (normalize stems)
        try:
            stem_id = self.stem2id[stem]
        except KeyError:
            stem_id = self.stem2id[stem] = self.new_id.next()

        return stem_id

    def _add_word(self, word, object_id, do_stem=True):

        # Get the stem and tail.
        if do_stem:
            stem = self.stem_word(word)
            tail = word.replace(stem, '', 1)
        else:
            stem = word

        stem_id = self.get_stem_id(stem)

        # Augment the index collection.
        self.index[stem_id].add(object_id)

        # Augment the tail collection.
        if do_stem and tail:
            self.tails[stem_id].add(tail)

        # If stem diffs from word, add word as well.
        if stem != word:
            stem_id = self.get_stem_id(word)
            self.index[stem_id].add(object_id)

    def add(self, object_type, objects, text_func=None, substrs=False,
            all_substrs=False, storekeys=None):

        object_store = self.objects
        #more_text = self.more_text
        for obj in objects:

            id_ = obj['_id']
            if storekeys:
                obj_ = dict(zip(storekeys, map(obj.get, storekeys)))
            else:
                obj_ = obj
            object_store[id_] = obj_

            text = text_func(obj)

            #text += more_text(obj)

            words = set(filter(self.f, re.findall(r'\w+', text.lower())))
            words = words - self.stopwords
            add_word = self._add_word

            for w in words:

                add_word(w, id_)

                if all_substrs:
                    for substring in substrings(w):
                        add_word(substring, id_, do_stem=False)

                elif substrs:
                    for substring in substrings(w, from_beginning_only=True):
                        add_word(substring, id_, do_stem=False)

    @property
    def id2stem(self):
        return dict(t[::-1] for t in self.stem2id.items())

    def jsondata(self):

        return {
            'stem2id': self.stem2id,
            'id2stem': self.id2stem,
            'index': dict((k, list(v)) for (k, v) in self.index.items()),
            'tails': dict((k, list(v)) for (k, v) in self.tails.items()),
            'objects': self.objects
            }

    def as_json(self, showsizes=False):
        data = self.jsondata()
        if showsizes:
            from utils import humanize_bytes
            for k, v in data.items():
                js = json.dumps(v, cls=JSONDateEncoder)
                print 'size of', k, humanize_bytes(sys.getsizeof(js))
        return data

    def dump(self, fp):
        json.dump(self.jsondata(), fp, cls=JSONDateEncoder)

    def query(self, word):
        stem = self.stem_word(word)
        stem_id = self.stem2id[stem]
        return self.index[stem_id]

    def qq(self, word):
        stem = self.stem_word(word)
        stem_id = self.stem2id[stem]
        pairs = self.index[stem_id]
        objects = self.objects
        for type_, id_ in pairs:
            yield objects[type_][id_]

    def more_text(self, obj, clean_html=nltk.clean_html):
        try:
            with open('billtext/{state}/{_id}'.format(**obj)) as f:
                html = f.read().decode('utf-8')
                return clean_html(html)
        except IOError:
            return ''


class JSONDateEncoder(json.JSONEncoder):
    """
    JSONEncoder that encodes datetime objects as Unix timestamps.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.utctimetuple())
        elif isinstance(obj, datetime.date):
            return time.mktime(obj.timetuple())

        return json.JSONEncoder.default(self, obj)


def substrings(word, from_beginning_only=False):
    '''A generator of all substrings in `word`
    greater than 1 character in length.'''
    w_len = len(word)
    w_len_plus_1 = w_len + 1
    i = 0
    while i < w_len:
        j = i + 2
        while j < w_len_plus_1:
            yield word[i:j]
            j += 1
        if from_beginning_only:
            return
        i += 1


def trie_add(values, trie=None, terminus=0):
    '''Given a trie (or rather, a dict), add the match terms into the
    trie.
    '''
    if trie is None:
        trie = {}

    for value in values:

        this = trie
        w_len = len(value) - 1
        for i, c in enumerate(value):

            try:
                this = this[c]
            except KeyError:
                this[c] = {}
                this = this[c]

            if i == w_len:
                this[terminus] = value

    return trie
