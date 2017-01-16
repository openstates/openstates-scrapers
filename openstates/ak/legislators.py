import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class AKLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ak'
    latest_only = True

    def _scrape_legislator(self, chamber, term, url):
        page = self.lxmlize(url)

        bio = page.xpath('//div[@class="bioright"]/a/..//text()')
        bio = {x.split(':')[0].strip(): x.split(':')[1].strip()
            for x in bio if x.strip()}

        capitol_office = [
            x.strip()
            for x in page.xpath('//div[@class="bioleft"]//text()')
            if x.strip()
        ]

        assert capitol_office[0] == 'Session Contact'
        assert capitol_office[3].startswith('Phone:')
        assert capitol_office[4].startswith('Fax:')

        leg.add_office(
            type = 'capitol',
            name = 'Capitol Office',
            address = capitol_office[1] + '\n' + capitol_office[2],
            phone = capitol_office[3][len('Phone: '): ] if
                len(capitol_office[3]) > len('Phone:') else None,
            fax = capitol_office[4][len('Fax: '): ] if
                len(capitol_office[4]) > len('Fax:') else None,
        )

        district_office = [
            x.strip()
            for x in page.xpath('//div[@class="bioright"][2]//text()')
            if x.strip()
        ]

        # Some members don't have district offices listed, so skip them
        if any('AK' in x for x in district_office):
            assert district_office[0] == 'Interim Contact'
            assert district_office[3].startswith('Phone:')
            assert district_office[4].startswith('Fax:')

            leg.add_office(
                type = 'district',
                name = 'District Office',
                address = district_office[1] + '\n' + district_office[2],
                phone = district_office[3][len('Phone: '): ] if
                    len(district_office[3]) > len('Phone:') else None,
                fax = district_office[4][len('Fax: '): ] if
                    len(district_office[4]) > len('Fax:') else None,
            )


    def scrape(self, chamber, term):
        self._party_map = {
            'Democrat': 'Democratic',
            'Republican': 'Republican',
            'Non Affiliated': 'Independent',
        }

        if chamber == 'upper':
            url = 'http://senate.legis.state.ak.us/'
        else:
            url = 'http://house.legis.state.ak.us/'

        page = self.lxmlize(url)

        items = page.xpath('//ul[@class="item lists"]/li')
        emails = page.xpath('//a[text()="Email Me"]/text()')
        if len(items) != len(emails):
            raise Exception('email address - item count mismatch')

        for item, email in zip(items, emails):
            photo_url = item.xpath('.//img/@src')[0]
            name = item.xpath('.//strong/text()')[0]
            leg_url = item.xpath('.//a/@href')[0]

            for dt in item.xpath('.//dt'):
                dd = dt.xpath('following-sibling::dd')[0].text_content()
                if dt.text == 'Party:':
                    party = dd
                elif dt.text == 'District:':
                    district = dd
                elif dt.text == 'Phone:':
                    phone = dd
                elif dt.text == 'Fax:':
                    fax = dd

            leg = Legislator(
                term=term,
                chamber=chamber,
                district=district,
                full_name=name,
                party=self._party_map[party],
                photo_url=photo_url,
                email=email,
            )
            leg.add_source(url)
            leg.add_source(leg_url)

            # scrape offices

            self.save_legislator(leg)
