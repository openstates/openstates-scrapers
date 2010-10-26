import csv
import argparse

from fiftystates.backend import db

def _extract(d, fields):
    rd = {}
    for f in fields:
        rd[f] = d.get(f, None)
    return rd

def check_state(state):
    legislators = db.legislators.find({
        'state': state,
    })

    fields = ('_id', 'first_name', 'last_name', 'state', 'chamber', 'district',
              'party', 'active', 'votesmart_id', 'nimsp_candidate_id')

    uniques = {'office': set(), 'votesmart_id':set(),
               'nimsp_candidate_id':set()}

    writer = csv.DictWriter(open(state+'.csv', 'w'), fields)

    writer.writerow(dict(zip(fields, fields)))

    for leg in legislators:

        writer.writerow(_extract(leg, fields))

        # check unique office
        if leg['active']:
            office = '-'.join((leg['chamber'], leg['district']))
            if office in uniques['office']:
                print 'Duplicates for office: %s' % office
            uniques['office'].add(office)

        # check other uniques
        for field in uniques.iterkeys():
            if field == 'office':
                pass
            if leg.get(field, None):
                if leg[field] in uniques[field]:
                    print 'duplicate for %s=%s' % (field, leg[field])
                uniques[field].add(leg[field])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='get a CSV of legislator data'
    )

    parser.add_argument('states', metavar='STATE', type=str, nargs='+',
                        help='states to dump')

    args = parser.parse_args()

    for state in args.states:
        check_state(state)
