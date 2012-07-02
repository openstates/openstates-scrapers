#!/usr/bin/env python

from billy import db

watch = [ 'ma', 'nj', 'il', 'ny' ]

for row in db.reports.find():
    if not row['_id'] in watch:
        continue

    for guy in [ 'bills' ]:
        for thing in [ 'updated_this_month', 'updated_today' ]:
            print "(%s) %s %s: %s" % ( row['_id'], guy, thing, row[guy][thing] )
    print ""
