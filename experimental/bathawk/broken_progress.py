import webbrowser
import itertools
import operator
from billy import db


def main(sciptname, abbr, session=None):

    spec = {
        'state': abbr,
        'action_dates.signed': {'$ne': None},
        '$or': [
            {'action_dates.passed_upper': None},
            {'action_dates.passed_lower': None}
            ]
        }

    if session is not None:
        spec['session'] = session

    bills = db.bills.find(spec)
    print 'Found', bills.count(), 'offending bills'
    bills = list(bills)

    if not session:
        grouper = operator.itemgetter('session')
        for session, _bills in itertools.groupby(bills, key=grouper):
            print session, '-', len(list(_bills)), 'offendings bills'

    raw_input("Press enter to view the offending bills: ")

    for bill in bills:
        url = 'http://localhost:8000/{state}/bills/{session}/{bill_id}/'.format(**bill)
        print bill['bill_id'], url
        print bill['action_dates']
        webbrowser.open(url)
        import pdb;pdb.set_trace()


if __name__ == '__main__':
    import sys
    main(*sys.argv)
