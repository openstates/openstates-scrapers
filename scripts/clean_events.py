#

from billy.core import db
#import sys

#state = sys.argv[1]

events = db.events.find({
#    "state": state
})

for event in events:
    dupes = db.events.find({
        "when": event['when'],
        "end": event['end'],
        "type": event['type'],
        "description": event['description']
    })
    for dupe in dupes:
        if dupe['_id'] == event['_id']:
            continue
        print "%s => %s (rm)" % (event['_id'], dupe['_id'])
        db.events.remove(dupe, safe=True)
