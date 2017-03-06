from __future__ import print_function
import os
import json
import glob
import itertools


def compare_dirs(dir1, dir2):
    files1 = glob.glob(dir1 + '/*.json')
    files2 = glob.glob(dir2 + '/*.json')

    f1set = set(f.replace(dir1, '') for f in files1)
    f2set = set(f.replace(dir2, '') for f in files2)

    only1 = f1set - f2set
    only2 = f2set - f1set

    if only1:
        print('some files only found in', dir1)
        for f in only1:
            print('   ', f)

    if only2:
        print('some files only found in', dir2)
        for f in only2:
            print('   ', f)

    if not only1 and not only2:
        both = f1set & f2set
        print(len(both), 'matched')

        compare_files(files1, files2)


def compare_json(val1, val2):
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
            print('differ on', k, v1, '!=', v2)


def compare_files(files1, files2):
    json1 = {os.path.basename(f): json.load(open(f)) for f in files1}
    json2 = {os.path.basename(f): json.load(open(f)) for f in files2}

    for key, val1 in json1.items():
        val2 = json2[key]
        compare_json(val1, val2)


def compare(dir1, dir2):
    for subdir in ('bills', 'legislators', 'committees', 'events'):
        compare_dirs(os.path.join(dir1, subdir), os.path.join(dir2, subdir))

    # don't compare vote filenames since they aren't static

if __name__ == '__main__':
    # TODO: votes
    # TODO: better reporting
    # TODO: easier to run
    compare('nc-billy/nc', 'nc-pupa2billy/nc')
