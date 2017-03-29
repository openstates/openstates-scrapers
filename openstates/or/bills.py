import datetime
import re
import logging

from pupa.scrape import Scraper, Bill
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone

logger = logging.getLogger('openstates')


class ORBillScraper(Scraper):
    jurisdiction = 'or'
    tz = get_timezone()

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'}

    chamber_code = {'S': 'upper', 'H': 'lower'}

    action_classifiers = (
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
            self.api_client.latest_session()

        yield from self.scrape_bills()

    def scrape_bills(self):
        measures_response = self.api_client.get('measures', page=500, session=self.session)

        legislators = index_legislators(self)

        for measure in measures_response:
            bid = '{} {}'.format(measure['MeasurePrefix'], measure['MeasureNumber'])

            chamber = self.chamber_code[bid[0]]
            bill = Bill(
                bid,
                legislative_session=self.session,
                chamber=chamber,
                title=measure['RelatingTo'],
                classification=self.bill_types[measure['MeasurePrefix'][1:]]
            )
            for sponsor in measure['MeasureSponsors']:
                legislator_code = sponsor['LegislatoreCode']  # typo in API
                if legislator_code:
                    try:
                        legislator = legislators[legislator_code]
                    except KeyError:
                        logger.warn('Legislator {} not found in session {}'.format(
                            legislator_code, self.session))
                        legislator = legislator_code
                    bill.add_sponsorship(
                        name=legislator,
                        classification={'Chief': 'primary', 'Regular': 'cosponsor'}[
                            sponsor['SponsorLevel']],
                        entity_type='person',
                        primary=True if sponsor['SponsorLevel'] == 'Chief' else False
                    )

            bill.add_source(
                "https://olis.leg.state.or.us/liz/{session}/Measures/Overview/{bid}".format(
                    session=self.session, bid=bid.replace(' ', ''))
            )
            for document in measure['MeasureDocuments']:
                try:
                    bill.add_version_link(document['VersionDescription'], document['DocumentUrl'],
                                          media_type='application/pdf')
                except ValueError:
                    logger.warn('Duplicate link found for {}'.format(document['DocumentUrl']))
            for action in measure['MeasureHistoryActions']:
                classifiers = self.determine_action_classifiers(action['ActionText'])
                when = datetime.datetime.strptime(action['ActionDate'], '%Y-%m-%dT%H:%M:%S')
                when = self.tz.localize(when)
                bill.add_action(action['ActionText'], when,
                                chamber=self.chamber_code[action['Chamber']],
                                classification=classifiers)

            yield bill

    def determine_action_classifiers(self, action):
        types = []
        for expr, types_ in self.action_classifiers:
            m = re.match(expr, action)
            if m:
                types += types_
        return types
