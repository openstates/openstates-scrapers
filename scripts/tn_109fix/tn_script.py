import sys

import pymongo
from billy.core import db

def main(state):

    spec = dict(state=state)

    print('fixing bills')
    bill_spec = dict(spec, session=108)
    for bill_109th in db.bills.find(bill_spec):
        print(bill_109th['bill_id'])
        # print(bill_109th['session'])
        # Reset session and _term to 108.
        bill_109th.update(session='108', _term='108')

        try:
            db.bills.save(bill_109th, w=1)
        except pymongo.errors.DuplicateKeyError:
            # This bill was duped, with the only different attr being
            # session value of 109. Merge the two bills by adding the
            # bad 109 bill id to the 108 bills' _all_ids.

            # First get the 108th session bill.
            spec = dict(spec,
                session='108',
                chamber=bill_109th['chamber'],
                bill_id=bill_109th['bill_id'])
            bill_108th = db.bills.find_one(spec)

            # Add the 109th id to its _all_ids.
            bill_109th_id = bill_109th['_id']
            bill_108th['_all_ids'].append(bill_109th_id)

            # Save.
            db.bills.save(bill_108th)
            db.bills.remove(bill_109th_id)


    # print('adding legislators')
    # for obj in db.legislators.find(spec):
    #     # Remove 108 and 109 from old roles. 108 are the current roles,
    #     # 109 are bogus.
    #     obj.get('old_roles', {}).pop('108', None)
    #     obj.get('old_roles', {}).pop('109', None)

    #     # Remove roles with term: 109.
    #     roles = obj.get('roles', [])
    #     for role in list(roles):
    #         if role['term'] == '109':
    #             roles.remove(role)

    #     db.legislators.save(obj)


if __name__ == "__main__":
    main('tn')








