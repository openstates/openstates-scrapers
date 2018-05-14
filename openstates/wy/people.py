import re
import json

import lxml.html
from pupa.scrape import Scraper, Person


class WYPersonScraper(Scraper):
    party_map = {'R':'republican', 'D':'democrat', 'I':'independent'}

    def scrape(self, chamber=None, session=None):
        session = self.latest_session()
        self.info('no session specified, using %s', session)

        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        chamber_abbrev = {'upper': 'S', 'lower': 'H'}[chamber]

        url = "https://wyoleg.gov/LsoService/api/legislator/2018/{}".format(chamber_abbrev)

        response = self.get(url)
        people_json = json.loads(response.content.decode('utf-8'))

        for row in people_json:
            party = self.party_map[row['party']]

            person = Person(
                name=row['name'],
                district=row['district'],
                party=party,
                primary_org=chamber,
                # given_name='first',
                # family_name='last',
            )

            if row['eMail']:
                person.add_contact_detail(type='email', value=row['eMail'])

            if row['phone']:
                person.add_contact_detail(type='voice', value=row['phone'])

            person.extras['wy_leg_id'] = row['legID']
            person.extras['county'] = row['county']

            # http://wyoleg.gov/Legislators/2018/S/2032
            leg_url = 'http://wyoleg.gov/Legislators/{}/{}/{}'.format(
                        session,
                        row['party'],
                        row['legID'])

            person.add_source(leg_url)
            person.add_link(leg_url)

            yield person
