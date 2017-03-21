from pupa.scrape import Person, Scraper
from .apiclient import OregonLegislatorODataClient


class ORPersonScraper(Scraper):
    jurisdiction = 'or'

    URLs = {
        "lower": "http://www.oregonlegislature.gov/house/Pages/RepresentativesAll.aspx",
        "upper": "http://www.oregonlegislature.gov/senate/Pages/SenatorsAll.aspx",
    }

    def scrape(self, chamber=None):

        self.api_client = OregonLegislatorODataClient(self)
        self._get_latest_session()

        yield from self.scrape_chamber()

    def scrape_chamber(self):
        legislators_reponse = self.api_client.get('legislators', session=self.session)

        for legislator in legislators_reponse:
            url_name = legislator['WebSiteUrl'].split('/')[-1]
            img = 'https://www.oregonlegislature.gov/house/MemberPhotos/{}.jpg'.format(url_name)
            person = Person(name='{} {}'.format(legislator['FirstName'], legislator['LastName']),
                            primary_org={'S': 'upper', 'H': 'lower'}[legislator['Chamber']],
                            party=legislator['Party'],
                            district=legislator['DistrictNumber'],
                            image=img)
            person.add_link(legislator['WebSiteUrl'])
            person.add_source(legislator['WebSiteUrl'])

            if legislator['CapitolAddress']:
                person.add_contact_detail(type='address', value=legislator['CapitolAddress'],
                                          note='Capitol Office')

            if legislator['CapitolPhone']:
                person.add_contact_detail(type='voice', value=legislator['CapitolPhone'],
                                          note='Capitol Office')

            person.add_contact_detail(type='email', value=legislator['EmailAddress'])
            person.add_contact_detail(type='url', value=legislator['WebSiteUrl'])

            yield person

    def _get_latest_session(self):
        self.session = self.api_client.get('sessions')[-1]['SessionKey']