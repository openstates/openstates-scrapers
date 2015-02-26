#!/usr/bin/env python

from billy.core import db
import us

states = (x.abbr.lower() for x in us.STATES)
HEADER = "committee,member,role,phone,email"

def extract(leg, key):
    x = leg.get(key, None)
    if x is not None:
        yield x
    for office in leg['offices']:
        x = office.get(key, None)
        if x is not None:
            yield x

def write(fd, keys):
    fd.write('"{}"'.format(",".join(keys)))

for state in states:
    with open("out/{}.csv".format(state), 'w') as fd:
        fd.write(HEADER)
        fd.write("\n")
        for committee in db.committees.find({"state": state}):
            committee_name = committee['committee']
            if committee['subcommittee'] is not None:
                committee_name = "{subcommittee} ({committee} subcommittee)".format(
                    **committee)
            for member in committee['members']:
                fd.write(u'"{}","{}","{}"'.format(
                    committee_name, member['name'], member['role']
                ).encode("utf-8"))
                lid = member['leg_id']
                if lid is not None:
                    leg = db.legislators.find_one({"_id": lid})
                    write(fd, extract(leg, 'phone'))
                    write(fd, extract(leg, 'email'))
                fd.write("\n")
