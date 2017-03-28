from pupa.scrape import VoteEvent, Scraper
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone


class ORVoteScraper(Scraper):

    tz = get_timezone()
    chamber_code = {'S': 'upper', 'H': 'lower'}

    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        self.session = session
        if not self.session:
            self.session = self.api_client.latest_session()

        yield from self.scrape_votes()

    def scrape_votes(self):
        measures_response = self.api_client.get('votes', session=self.session)

        for measure in measures_response:
            bid = '{} {}'.format(measure['MeasurePrefix'], measure['MeasureNumber'])
            chamber = self.chamber_code[bid[0]]
            measure_vote_response = measure['MeasureVote']
            if not measure_vote_response:
                continue

            vote = VoteEvent(
                start_date=measure_vote_response[0]['ActionDate'],
                bill_chamber=chamber,
                motion_text=measure_vote_response[0]['ActionText'],
                classification='passage',

            )

            for vote_resp in measure_vote_response:
                pass

            vote = VoteEvent(
                start_date=when,
                bill_chamber=chamber,
                motion_text=action,
                classification='passage',
                result='pass' if passed else 'fail',
                legislative_session=session,
                bill=bid,
                chamber=action_chamber
            )

            yield vote