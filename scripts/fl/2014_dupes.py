'''
Plan
-----

for each 2013 bill, if id starts with "H " or "S ",

'''
import pymongo
from billy.core import db

def action2tuple(action):
    ac = map(action.get, ['action', 'actor', 'date'])
    ac.append('-'.join(action['type']))
    return tuple(ac)


def main():

    spec = dict(state='fl', session='2014')

    print('fixing bills')
    for dupe in db.bills.find(spec):
        dupe_bill_id = dupe['bill_id']

        letter, number = dupe_bill_id.split(' ', 1)
        if len(letter) is 1:

            regex = ur'%s[A-Z]* %s$' % (letter, number)
            spec = {
                'state': 'fl',
                'session': '2014',
                'bill_id': {'$regex': regex},
                'title': dupe['title']}
            bills_2014 = list(db.bills.find(spec))

            same_actions = []
            dupe_actionset = set(map(action2tuple, dupe['actions']))
            for mergebill in bills_2014:
                if mergebill == dupe:
                    continue
                mergebill_actions = map(action2tuple, mergebill['actions'])
                if dupe_actionset.issubset(mergebill_actions):
                    same_actions.append(mergebill)

            if not same_actions:
                print 'no dupes for', dupe['bill_id']
                continue

            if not len(same_actions) == 1:
                print "CRAAAAAP"
                import pdb; pdb.set_trace()
            else:
                mergebill = same_actions.pop()

            print 'merging %s into %s' % (dupe['bill_id'], mergebill['bill_id'])
            mergebill['_all_ids'].append(dupe['_id'])

            db.bills.save(mergebill, w=1)
            db.bills.remove(dupe['_id'])

        else:
            print("Not merging %s" % dupe['bill_id'])



if __name__ == "__main__":
    main()








