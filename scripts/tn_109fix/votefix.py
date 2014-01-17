import sys

import pymongo

try:
    from billy.core import db
except:
    db = pymongo.MongoClient().fiftystates


def main(state):

    spec = dict(state=state)
    for vote in db.votes.find(spec):
        if vote['session'] in ('109'):
            vote['session'] = '108'
            print('fixing', vote['_id'])
            db.votes.save(vote, w=1)



if __name__ == "__main__":
    main('tn')








