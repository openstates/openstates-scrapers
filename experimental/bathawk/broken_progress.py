import webbrowser
import itertools
import operator
from billy.core import db


def main(abbr, session=None):

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
    yield bills.count()
    bills = list(bills)
    yield bills
    if not session:
        grouper = operator.itemgetter('session')
        for session, _bills in itertools.groupby(bills, key=grouper):
            yield session, len(list(_bills))


if __name__ == '__main__':
    import sys

    from clint.textui import puts, indent
    from clint.textui.colored import green, yellow, red

    if not sys.argv[1:]:
        for meta in db.metadata.find():
            abbr = meta['_id']
            data = main(abbr)
            bogus = data.next()
            bills = data.next()
            if not bogus:
                puts(green('%s: ok!' % abbr))
                continue
            msg = '%s: Found %s bills with progress gaps...'
            puts(msg % (green(abbr), red(str(bogus))))
            with indent(2):
                for session, total in data:
                    vals = (yellow(session), red(total))
                    puts('|-%s: %s' % vals)

    else:
        abbr = sys.argv[1]
        data = main(abbr)
        bogus = data.next()
        bills = data.next()
        if not bogus:
            puts(green('%s: ok!' % abbr))
            sys.exit(1)
        msg = '%s: Found %s bills with progress gaps...'
        puts(msg % (green(abbr), red(str(bogus))))
        with indent(2):
            for session, total in data:
                vals = (yellow(session), red(total))
                puts('|-%s: %s' % vals)

        raw_input("Press enter to view the offending bills: ")

        for bill in bills:
            url = 'http://localhost:8000/{state}/bills/{session}/{bill_id}/'.format(**bill)
            print bill['bill_id'], url
            print bill['action_dates']
            webbrowser.open(url)
            import pdb;pdb.set_trace()
