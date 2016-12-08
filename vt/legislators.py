import json

from billy.scrape.legislators import Legislator, LegislatorScraper
from openstates.utils import LXMLMixin


class VTLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'vt'
    latest_only = True
    CHAMBERS = {'Senator': 'upper', 'Representative': 'lower'}

    def scrape(self, term, chambers):
        year_slug = term[5:]

        # Load all members via the private API
        legislator_dump_url = (
            'http://legislature.vermont.gov/people/loadAll/{}'.
            format(year_slug))
        json_data = self.get(legislator_dump_url).text
        legislators = json.loads(json_data)['data']

        # Parse the information from each legislator
        for info in legislators:
            # Strip whitespace from strings
            info = {k: v.strip() for k, v in info.iteritems()}

            # Gather photo URL from the member's page
            member_url = ('http://legislature.vermont.gov/people/single/{}/{}'.
                          format(year_slug, info['PersonID']))
            page = self.lxmlize(member_url)
            (photo_url, ) = page.xpath('//img[@class="profile-photo"]/@src')

            # Also grab their state email address
            state_email = page.xpath(
                '//dl[@class="summary-table profile-summary"]/'
                'dt[text()="Email"]/following-sibling::dd[1]/a/text()')
            if state_email:
                (state_email, ) = state_email
            else:
                state_email = None

            leg = Legislator(
                term=term,
                chamber=self.CHAMBERS[info['Title']],
                district=info['District'].replace(" District", ""),
                party=info['Party'].replace("Democrat", "Democratic"),
                full_name="{0} {1}".format(info['FirstName'], info['LastName']),
                photo_url=photo_url
            )

            leg.add_office(
                type='capitol',
                name='Capitol Office',
                address='Vermont State House\n115 State Street\nMontpelier, VT 05633',
                email=state_email
            )

            leg.add_office(
                type='district',
                name='District Office',
                address="{0}{1}\n{2}, {3} {4}".format(
                    info['MailingAddress1'],
                    ("\n" + info['MailingAddress2']
                        if info['MailingAddress2'].strip()
                        else ""),
                    info['MailingCity'],
                    info['MailingState'],
                    info['MailingZIP']
                ),
                phone=(info['HomePhone'].strip() or None),
                email=(info['Email'].strip() or
                       info['HomeEmail'].strip() or
                       info['WorkEmail'].strip() or
                       None)
            )

            leg.add_source(legislator_dump_url)
            leg.add_source(member_url)

            self.save_legislator(leg)
