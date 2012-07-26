from collections import defaultdict, OrderedDict, namedtuple
from decimal import Decimal
from operator import itemgetter

from billy import db


KEYS = 'versions actions documents votes sponsors'.split()


class SaneReprList(list):
    def __repr__(self):
        return '<SaneReprList: %d elements>' % len(self)


class Summarizer(object):

    def __init__(self, spec={}):
        self.spec = spec

    def build(self, keys=KEYS):
        listdict = lambda: defaultdict(SaneReprList)
        counts = defaultdict(listdict)

        keys = 'versions actions documents votes sponsors'.split()
        for bill in db.bills.find(self.spec):
            for k in keys:
                counts[k][len(bill[k])].append(bill['_id'])

        self.counts = dict(counts)
        return dict(counts)

    def count(self):
        return db.bills.find(self.spec).count()

    def max_ids(self):
        '''Yield the key, maximum value length, and the id of the
        bill in which the max was found for each key in KEYS. In
        other words, if TAB0000001 has the most actions (345), then
        one tuple yielded from this generator would be:
        ('actions', 345, 'TAB0000001')
        '''
        for k, v in self.counts.items():
            max_ = max(v)
            id_ = v[max_]
            yield k, max_, id_

    def mean(self, key):
        counts = self.counts[key]
        sum_ = sum(k * len(v) for (k, v) in counts.items())
        return sum_ / self.count()

    def median(self, key):
        counts = self.counts[key]
        if 1 < len(counts):
            counts = self.counts[key]
            div, mod = divmod(len(counts), 2)
            return div
        else:
            return list(counts).pop()

    def mode(self, key):
        counts = self.counts[key]
        if 1 < len(counts):
            return (max(counts) + min(counts)) / 2
        else:
            return list(counts).pop()

    def percentages(self, key):
        '''Returns an OrderedDict where the keys are the numbers of
        actions/votes found and the values are the percentages of how
        many bills had that number of actions out of the total number
        of bills.
        '''
        counts = self.counts[key]
        sum_ = Decimal(self.count())
        items = ((k, (len(v) / sum_) * 100) for (k, v) in counts.items())
        sorter = itemgetter(slice(None, None, -1))
        items = sorted(items, key=sorter, reverse=True)
        return OrderedDict(items)

    def report(self):
        Stats = namedtuple('Stats', 'mean median mode percentages')
        methods = [self.mean, self.median, self.mode, self.percentages]
        return dict((key, Stats(*[meth(key) for meth in methods])) for key in KEYS)

    def print_report(self):
        tab = '    '
        for k, v in self.report().items():
            print
            print repr(k)
            for key in ('mean', 'median', 'mode'):
                print tab, key, '->', getattr(v, key)
            print
            print tab, 'Percentage breakdown'
            for value, percentage in v.percentages.items():
                print tab * 2, value, "{0:.2f}".format(percentage)


if __name__ == '__main__':
    # import pprint
    # pprint.pprint(get_counts())
    x = Summarizer()
    x.build()
    x.print_report()
