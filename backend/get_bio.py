#!/usr/bin/env python
from couchdb.client import Server
import argparse
from votesmart import votesmart
from schemas import Legislator, StateMetadata


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

    metadata = StateMetadata.get(db)

    # We expect the passed in year to be an election year, so find
    # the session corresponding to that election
    session = metadata.session_for_election(int(year))
    assert session

    # Get list of officials from votesmart
    candidates = []
    for officeId in [7, 8, 9]:
        try:
            candidates.extend(
                votesmart.candidates.getByOfficeState(officeId, state.upper(),
                                                      electionYear=year))
        except:
            pass
    elected = filter(lambda cand: cand.electionStatus == 'Won', candidates)
    officials = {}
    for official in elected:
        if official.lastName in officials:
            officials[official.lastName].append(official)
        else:
            officials[official.lastName] = [official]

    # Go through CouchDB legislators
    # We grab all legislators for the session following the election year.
    # While this will get some unneeded docs but only involves one (Couch)
    # round trip, while searching separately for each official
    # returned by Vote Smart would involve many round trips.
    for leg in Legislator.for_session(db, session):
        if 'votesmart' in leg._data and not replace:
            # We already have data for this legislator (and don't
            # want to replace it)
            continue

        if leg.last_name in officials:
            for match in officials[leg.last_name]:
                if match.title == metadata.lower_title:
                    chamber = 'lower'
                else:
                    chamber = 'upper'

                if (match.firstName == leg.first_name and
                    chamber == leg.chamber):
                    # Found match
                    log("Getting bio data for %s (%s)" %
                        (leg.full_name, leg.chamber))

                    bio = votesmart.candidatebio.getBio(match.candidateId)
                    leg._data['votesmart'] = bio.__dict__
                    leg.store(db)

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
