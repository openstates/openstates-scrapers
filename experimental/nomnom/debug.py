import re
import pprint
from collections import defaultdict

from rpy2.robjects import r as rr
from rpy2.robjects import NA_Integer, StrVector
from rpy2.robjects.packages import importr

from billy.core import mdb
from billy.models.bills import Bill


base = importr('base')
pscl = importr('pscl', lib_loc='~/code/R/')


class Rollcall(object):

    def __init__(self, spec, yea=1, nay=0, not_in_legis=9,
                 legis_names=None, vote_names=None,
                 legis_data=None, vote_data=None,
                 desc=None, source=None):
        self.spec = spec
        self.chamber = spec['chamber']
        self.yea = yea
        self.nay = nay
        # self.missing = missing
        # self.not_in_legis = not_in_legis
        self.legis_names = legis_names
        self.vote_names = vote_names
        self.legis_data = legis_data
        self.vote_data = vote_data
        self.desc = desc
        self.source = source

    def is_bill(self, bill):
        return not re.search(r'A|S', bill['bill_id'])

    def get_data(self):
        '''Must return a nested dict like:
            {'vote_id': {'leg_id1': 'vote_val1', ...}}
        '''
        data = defaultdict(dict)
        chamber = self.chamber
        for bill in mdb.bills.find(spec).limit(3000):
            for vote in bill.votes_manager():

                # Skip votes for the other chamber.
                if vote['chamber'] != chamber:
                    continue

                column = data[vote['vote_id']]
                keyvals = (('yes_votes', self.yea),
                           ('no_votes', self.nay))
                for key, val in keyvals:
                    votes = vote[key]
                    for v in votes:
                        if v['leg_id'] is None:
                            continue
                        column[v['leg_id']] = val
        return data

    def _build_matrix(self):
        '''Produce an R matrix from the votes data.
        '''
        leg_id_set = set()
        vote_id_set = set()
        nrows = []
        data = self.get_data()
        for vote_id, rowdata in data.items():
            vote_id_set.add(vote_id)
            count = 0
            for leg_id, vote_val in rowdata.items():
                leg_id_set.add(leg_id)
                count += 1
            nrows.append(count)

        self.leg_ids = leg_ids = sorted(leg_id_set)
        self.vote_ids = vote_ids = sorted(vote_id_set)

        matrix = base.matrix(NA_Integer, nrow=len(leg_ids), ncol=len(data))
        for col_i, vote_id in enumerate(vote_ids):
            for row_i, leg_id in enumerate(leg_ids):
                val = data[vote_id].get(leg_id)
                if val:
                    matrix.rx[row_i, col_i] = val

        import pdb; pdb.set_trace()
        return matrix

    def rollcall(self):
        matrix = self._build_matrix()
        kwargs = {
            'data': matrix,
            # 'legis.names': StrVector(self.leg_ids),
            }
        return pscl.rollcall(**kwargs)

spec = dict(state='ny', session='2013-2014', chamber='lower')
print 'creating rollcall..'
rollcall = Rollcall(spec).rollcall()
print '..done'
print 'dropping unanimous..'
pscl.dropUnanimous(rollcall)
print '..done'

print 'ideal..'
ideal = pscl.ideal(rollcall)
print '..done'
import pdb; pdb.set_trace()
