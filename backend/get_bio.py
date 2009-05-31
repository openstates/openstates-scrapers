#!/usr/bin/env python
from couchdb.client import Server
import argparse
from votesmart import votesmart


votesmart.apikey = 'API_KEY'


def get_bio(state, year, replace=True, verbose=False):
    """
    Get biographical data from Project Vote Smart on state legislators elected
    in the given state during the given year.
    """

    def log(msg):
        if verbose:
            print "%s: %s" % (state, msg)

    # Setup couch connection
    server = Server('http://localhost:5984')
    assert state in server
    db = server[state]

    # Get list of reps from votesmart
    candidates = votesmart.candidates.getByOfficeState(8, state.upper(),
                                                       electionYear=year)
    elected = filter(lambda cand: cand.electionStatus == 'Won', candidates)
    officials = {}
    for official in elected:
        if official.lastName in officials:
            officials[official.lastName].append(official)
        else:
            officials[official.lastName] = [official]

    # Go through CouchDB legislators
    # This currently won't work with states which don't use years to
    # name sessions.
    # Also we miss some legislators because of an off-by-one error
    # between election year and the year the session actually starts.
    for leg in db.view('app/leg-by-year', include_docs=True)[int(year)]:
        doc = leg.doc

        if 'votesmart' in doc and not replace:
            continue

        if doc['last_name'] in officials:
            for match in officials[doc['last_name']]:
                # This is not state-agnostic:
                if match.title == 'Representative':
                    chamber = 'lower'
                else:
                    chamber = 'upper'

                if (match.firstName == doc['first_name'] and
                    chamber == doc['chamber']):
                    # Found match
                    log("Getting bio data for %s (%s)" %
                        (doc['fullname'], doc['chamber']))

                    bio = votesmart.candidatebio.getBio(match.candidateId)
                    doc['votesmart'] = bio.__dict__
                    db.update([doc])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Grab biographical information on state legislators")
    parser.add_argument('--year', '-y', action='append')
    parser.add_argument('states', metavar='state', nargs='+',
                        help='the state(s) to import')
    parser.add_argument('--replace', '-r', action='store_true',
                        help='replace biographical data if it already exists')
    parser.add_argument('-v', '--verbose', action='store_true')
    # TODO: couch host option, maybe option for non-default DB name

    args = parser.parse_args()

    for state in args.states:
        for year in args.year:
            get_bio(state, year, args.replace, args.verbose)
