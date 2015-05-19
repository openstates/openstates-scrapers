'''
This script will print out "duplicate" legislators that could cause
a SameNameError in the OS->OCD conversion. Some of these aren't true
duplicates, so don't take this list as truth! For example, there
actually _are_ two Phil Williams in the Alabama legislature.
'''

from billy.core import db


for state in db.legislators.distinct("state"):
    legislators = db.legislators.find({'state': state})
    names = set()
    dup_names = []

    print("----Processing {} ({} legislators total)----".format(
        state, legislators.count()))

    for legislator in legislators:
        full_name = legislator['full_name']
        scraped_name = legislator['_scraped_name']

        if full_name in names or scraped_name in names:
            dup_names.append(full_name)
        else:
            names.add(full_name)
            names.add(scraped_name)

    for name in sorted(dup_names):
        print("{}    {}".format(state, name.encode('utf-8')))
