from __future__ import print_function
import os
import re
import sys
import json
import glob
import itertools
from collections import defaultdict


class Comparator:
    def __init__(self, objtype):
        self.objtype = objtype
        self.compared = 0
        self.differed = 0

    def summary(self):
        print(self.objtype, self.differed, 'differed out of', self.compared)

    def compare_json(self, key, val1, val2):
        differed = 0
        for k, v1 in val1.items():
            v2 = val2.get(k)
            if self.objtype == 'bills' and k == 'votes':
                # we'll compare votes later
                continue
            elif k == 'sponsors':
                for v in itertools.chain(v1, v2):
                    v.pop('chamber', None)
            elif k == 'versions' or k == 'documents':
                for v in itertools.chain(v1, v2):
                    v.pop('date', None)
            elif k in ('yes_votes', 'no_votes', 'other_votes'):
                v1 = sorted(v1)
                v2 = sorted(v2)
            elif k == 'actions':
                for v in itertools.chain(v1, v2):
                    v['type'] = sorted([t for t in v['type'] if t != 'other'])
                for i, (a1, a2) in enumerate(zip(v1, v2)):
                    a1.pop('date')
                    a2.pop('date')
                    if a1 != a2:
                        print('action', i, 'differ', a1, '!=', a2)

                # don't do the normal check for actions
                continue

            if v1 != v2:
                print(key, 'differ on', k, v1, '!=', v2)
                differed = 1

        self.differed += differed
        self.compared += 1

    def load_json(self, dirname):
        """ dirname => {key: jsonobj} """
        files = glob.glob(os.path.join(dirname, self.objtype) + '/*.json')
        return {os.path.basename(f): json.load(open(f)) for f in files}

    def compare(self, dir1, dir2):
        files1 = self.load_json(dir1)
        files2 = self.load_json(dir2)

        k1set = set(files1.keys())
        k2set = set(files2.keys())

        only1 = k1set - k2set
        only2 = k2set - k1set

        if only1:
            print(self.objtype, 'some files only found in old')
            for f in only1:
                print('   ', f)
        if only2:
            print(self.objtype, 'some files only found in new')
            for f in only2:
                print('   ', f)

        for key in k1set & k2set:
            self.compare_json(key, files1[key], files2[key])

        self.summary()


def fix_bill_id(bill_id):
    bill_id = bill_id.replace('.', '')
    _bill_id_re = re.compile(r'([A-Z]*)\s*0*([-\d]+)')
    return _bill_id_re.sub(r'\1 \2', bill_id, 1).strip()


class VoteComparator(Comparator):
    def load_json(self, dirname):
        """ dirname => {key: jsonobj} """
        files = glob.glob(os.path.join(dirname, self.objtype) + '/*.json')
        blobs = [json.load(open(f)) for f in files]
        if not blobs:
            # no votes, try loading bills
            files = glob.glob(os.path.join(dirname, 'bills') + '/*.json')
            bills = [json.load(open(f)) for f in files]
            blobs = []
            for bill in bills:
                for v in bill.get('votes'):
                    v['bill_id'] = fix_bill_id(bill['bill_id'])
                    blobs.append(v)
        all_json = defaultdict(list)
        for d in blobs:
            key = (fix_bill_id(d['bill_id']), d['motion'].strip())
            all_json[key].append(d)
        return all_json

    def compare_json(self, key, val1, val2):
        for i, (v1, v2) in enumerate(zip(sorted(val1, key=lambda x: (x['date'], x['yes_count'])),
                                         sorted(val2, key=lambda x: (x['date'], x['yes_count'])))):
            super(VoteComparator, self).compare_json(key + (i,), v1, v2)


def compare(dir1, dir2):
    for objtype in ('bills', 'legislators', 'committees'):
        c = Comparator(objtype)
        c.compare(dir1, dir2)

    vc = VoteComparator('votes')
    vc.compare(dir1, dir2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('./compare.py <dir1> <dir2>')
        sys.exit(1)
    compare(sys.argv[1], sys.argv[2])
