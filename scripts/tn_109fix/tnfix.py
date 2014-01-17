import sys
import plop
import pymongo


def main(state):
    db = pymongo.MongoClient().fiftystates
    index = plop.Index()

    spec = dict(state=state)
    print('adding bills')
    for bill in db.bills.find(spec):
        index.add_object(bill)

    print('adding legislators')
    for obj in db.legislators.find(spec):
        index.add_object(obj)

    print('adding committees')
    for obj in db.committees.find(spec):
        index.add_object(obj)

    print('adding votes')
    for obj in db.votes.find(spec):
        index.add_object(obj)

    import pdb; pdb.set_trace()


if __name__ == "__main__":
    main(*sys.argv[1:])

