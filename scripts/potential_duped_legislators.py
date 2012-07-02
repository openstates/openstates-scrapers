#!/usr/bin/env python

from sunlight import openstates
import sys
import codecs
sys.stdout=codecs.getwriter('utf-8')(sys.stdout)

state = sys.argv[1]

kwargs = {
    "state": state
}

legis = openstates.legislators(**kwargs)
for leg in legis:
    search = openstates.legislators(
        first_name=leg['first_name'],
        last_name=leg['last_name'],
        active="false",
        state=state
    )
    for s in search:
        if s['leg_id'] != leg['leg_id']:
            print s['full_name']
            print leg['full_name']
            print "  %s / %s" % (
                s['leg_id'], leg['leg_id']
            )
            print ""
