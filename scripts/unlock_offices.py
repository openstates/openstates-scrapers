import csv
import sys
from collections import defaultdict
from billy.core import db



def main(state):
    for leg in db.legislators.find({"state": state,
                                    "_locked_fields": "offices",
                                    "offices": []}):
        print("Locked blank office'd {leg_id}".format(**leg))
        leg['_locked_fields'].remove('offices')
        db.legislators.save(leg)


if __name__ == "__main__":
    main(*sys.argv[1:])
