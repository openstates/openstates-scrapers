import functools
import re
from operator import itemgetter

from utils import CachedAttr

class Trie(dict):

    @CachedAttr
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
