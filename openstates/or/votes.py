import re
from collections import Counter

from pupa.scrape import VoteEvent, Scraper
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone


class ORVoteScraper(Scraper):

    tz = get_timezone()
    chamber_code = {'S': 'upper', 'H': 'lower'}
    vote_code = {'Aye': 'yes', 'Nay': 'no', 'Excused': 'absent'}

    vote_classifiers = (
        ('.*Introduction and first reading.*',
         ['introduction', 'reading-1']),

        ('.*First reading.*', ['introduction', 'reading-1']),
        ('.*Second reading.*', ['reading-2']),
        ('.*Referred to .*', ['referral-committee']),
        ('.*Assigned to Subcommittee.*', ['referral-committee']),
        ('.*Recommendation: Do pass.*', ['committee-passage-favorable']),
        ('.*Governor signed.*', ['executive-signature']),
        ('.*Third reading.* Passed', ['passage', 'reading-3']),
        ('.*Third reading.* Failed', ['failure', 'reading-3']),
        ('.*President signed.*', ['passage']),
        ('.*Speaker signed.*', ['passage']),
        ('.*Final reading.* Adopted', ['passage']),
        ('.*Read third time .* Passed', ['passage', 'reading-3']),
        ('.*Read\. .* Adopted.*', ['passage']),
    )


    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        self.session = session
        if not self.session:
            self.session = self.api_client.latest_session()

        yield from self.scrape_votes()

    def scrape_votes(self):
        measures_response = self.api_client.get('votes', session=self.session)

        legislators = index_legislators(self)

        for measure in measures_response:
            bid = '{} {}'.format(measure['MeasurePrefix'], measure['MeasureNumber'])

            measure_history = measure['MeasureHistoryActions']
            for event in measure_history:
                if event['MeasureVotes']:

                    tally = dict(Counter([self.vote_code[v['Vote']] for v in event['MeasureVotes']]))
                    passed = (float(tally['yes']) / (tally['yes'] + tally['no']) > 0.5)

                    classification = self.determine_vote_classifiers(event['ActionText'])
                    print(classification)
                    vote = VoteEvent(
                        start_date=event['ActionDate'],
                        bill_chamber=self.chamber_code[bid[0]],
                        motion_text=event['ActionText'],
                        classification=classification,
                        result='pass' if passed else 'fail',
                        legislative_session=self.session,
                        bill=bid,
                        chamber=self.chamber_code[measure_history['Chamber']]
                    )

                    vote.set_count('yes', tally['yes'])
                    vote.set_count('no', tally['yes'])
                    vote.set_count('absent', tally['absent'])

                    for voter in event['MeasureVotes']:
                        if voter['Vote'] == 'Aye':
                            vote.yes(legislators[voter['LegislatorCode']])
                        elif voter['Vote'] == 'Nay':
                            vote.no(legislators[voter['LegislatorCode']])
                        else:
                            vote.vote('absent', legislators[voter['LegislatorCode']])

                    yield vote

            committee_history = measure['CommitteeAgendaItems']
            for event in committee_history:
                pass  # TODO: finish this second vote section up

    def determine_vote_classifiers(self, vote):
        types = []
        for expr, types_ in self.vote_classifiers:
            m = re.match(expr, vote)
            if m:
                types += types_
        return types