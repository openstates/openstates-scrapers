from __future__ import print_function
import os
import sys
import json
import glob
import itertools


class Comparator:
    def __init__(self, objtype):
        self.objtype = objtype
        self.compared = 0
        self.differed = 0

    def summary(self):
        print(self.objtype, self.differed, 'differed out of', self.compared)

    def compare_json(self, key, val1, val2):
        for k, v1 in val1.items():
            v2 = val2.get(k)
            if k == 'sponsors':
                for v in itertools.chain(v1, v2):
                    v.pop('chamber', None)
            elif k == 'versions' or k == 'documents':
                for v in itertools.chain(v1, v2):
                    v.pop('date', None)
            elif k == 'actions':
                for v in itertools.chain(v1, v2):
                    if 'other' in v['type']:
                        v['type'] = [t for t in v['type'] if t != 'other']
            if v1 != v2:
                print(key, 'differ on', k, v1, '!=', v2)
                self.differed += 1
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


class VoteComparator(Comparator):
    def load_json(self, dirname):
        """ dirname => {key: jsonobj} """
        files = glob.glob(os.path.join(dirname, self.objtype) + '/*.json')
        blobs = [json.load(open(f)) for f in files]
        all_json = {}
        for d in blobs:
            key = (d['bill_id'], d['motion'])
            if key in all_json:
                # TODO: possible to fix by keeping both around and checking them
                print('duplicate key in votes, not all votes will get checked: ', key)
            all_json[key] = d
        return all_json


def compare(dir1, dir2):
    for objtype in ('bills', 'legislators', 'committees', 'events'):
        c = Comparator(objtype)
        c.compare(dir1, dir2)

    vc = VoteComparator('votes')
    vc.compare(dir1, dir2)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('./compare.py <dir1> <dir2>')
        sys.exit(1)
    compare(sys.argv[1], sys.argv[2])
