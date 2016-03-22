import re
import lxml.html
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.utils import LXMLMixin


class AKLegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'ak'
    latest_only = True

    def _scrape_legislator(self, chamber, term, url):
        page = self.lxmlize(url)

        (_title, name) = page.xpath(
            '//div[@class="holder-legislator"]/h1/text()')
        (photo_url, ) = page.xpath('//div[@class="bioleft"]/img/@src')
        
        bio = page.xpath('//div[@class="bioright"]/a/..//text()')
        bio = {x.split(':')[0].strip(): x.split(':')[1].strip()
            for x in bio if x.strip()}

        email = bio['Email']
        district = bio['District']
        party = self._party_map[bio['Party']]

        leg = Legislator(
            term = term,
            chamber = chamber,
            district = district,
            full_name = name,
            party = party,
            photo_url = photo_url
        )
        leg.add_source(url)

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

        self.save_legislator(leg)

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

        for link in page.xpath('//ul[@class="item lists"]/li/a/@href'):
            self._scrape_legislator(chamber, term, link)
