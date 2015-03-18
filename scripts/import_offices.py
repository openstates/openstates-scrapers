"""
Given a CSV in the form of:

id - Open States "Big ID" of the person


Any / all of:

  "{type}_{key}"

  where {type} is one of "capitol" or "district"
  where {key} is one of:
    - address
    - phone
    - fax
    - email
    - phone
    - name

One side-effect of this is it *will* lock the offices field for this person,
so ensure that this is a complete set of all the data that you need.
"""

import csv
import sys
from collections import defaultdict

from billy.core import db

CRUFT = ['ignore', '']

def parse(key):
    leader, val = key.split("_", 1)
    if leader not in ['district', 'capitol']:
        raise ValueError("Error: Bad leader for {}".format(key))
    return (leader, val)


def normalize(value):
    for raw, new in (
        ("\\n", "\n"),
        ("\\r", "\r"),
        ("\\t", "\t"),
    ):
        value = value.replace(raw, new)
    return value



def main(fpath, force="false"):
    force = True if force.lower() == "force" else False

    with open(fpath, 'r') as fd:
        for line in csv.DictReader(fd):
            id_ = line.pop("id").strip()
            if not id_:
                print("Error: Failure on {}".format(line))
                raise ValueError

            leg = db.legislators.find_one({"_all_ids": id_})
            if leg is None:
                print("NO SUCH PERSON! {}".format(id_))
                raise Exception

            locked = leg.get('_locked_fields', [])
            if 'offices' in locked and force is False:
                print("{_id} is already locked - skipping. Please unlock".format(
                    **leg))
                continue

            offices = defaultdict(dict)
            for k, v in line.items():
                if not v.strip() or k in CRUFT:
                    continue
                el, val = parse(k)

                offices[el][val] = normalize(v)

            new_offices = []
            for type_, office in offices.items():
                office['type'] = type_

                if 'name' not in office:
                    office['name'] = "{} Office".format(type_.title())

                new_offices.append(office)

            if new_offices == []:
                print("Yikes! Empty data; bailing")
                continue

            leg['offices'] = new_offices

            locked.append("offices")
            locked = list(set(locked))

            leg['_locked_fields'] = locked
            db.legislators.save(leg)
            print(id_)


if __name__ == "__main__":
    main(*sys.argv[1:])
