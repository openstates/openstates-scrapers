import re

from billy.utils import urlescape
from billy.scrape import NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html

class ARLegislatorScraper(LegislatorScraper):
    _remove_special_case = True
    jurisdiction = 'ar'
    latest_only = True

    def scrape(self, chamber, term):

        # Get start year of term.
        for termdict in self.metadata['terms']:
            if termdict['name'] == term:
                break
        start_year = termdict['start_year']

        url = ('http://www.arkleg.state.ar.us/assembly/%s/%sR/Pages/'
               'LegislatorSearchResults.aspx?member=&committee=All&chamber=')
        url = url % (start_year, start_year)
        page = self.get(url).text
        root = lxml.html.fromstring(page)

        for a in root.xpath('//table[@class="dxgvTable"]'
                            '/tr[contains(@class, "dxgvDataRow")]'
                            '/td[1]/a'):
            member_url = urlescape(a.attrib['href'])
            self.scrape_member(chamber, term, member_url)

    def scrape_member(self, chamber, term, member_url):
        page = self.get(member_url).text
        root = lxml.html.fromstring(page)

        name_and_party = root.xpath(
            'string(//td[@class="SiteNames"])').split()

        title = name_and_party[0]
        if title == 'Representative':
            chamber = 'lower'
        elif title == 'Senator':
            chamber = 'upper'

        full_name = ' '.join(name_and_party[1:-1])

        party = name_and_party[-1]

        if party == '(R)':
            party = 'Republican'
        elif party == '(D)':
            party = 'Democratic'
        elif party == '(G)':
            party = 'Green'
        elif party == '(I)':
            party = 'Independent'

        else:
            raise AssertionError(
                "Unknown party ({0}) for {1}".format(party, full_name))

        try:
            img = root.xpath('//img[@class="SitePhotos"]')[0]
            photo_url = img.attrib['src']
        except IndexError:
            """ Fix me after ?member=Boyd is fixed """
            self.warning("Uch, bad photo. Ducking")
            photo_url = ""

        # Need to figure out a cleaner method for this later
        info_box = root.xpath('string(//table[@class="InfoTable"])')
        district = re.search(r'District(.+)\r', info_box).group(1)

        leg = Legislator(term, chamber, district, full_name, party=party,
                         photo_url=photo_url, url=member_url)
        leg.add_source(member_url)

        try:
            phone = re.search(r'Phone(.+)\r', info_box).group(1)
        except AttributeError:
            phone = None
        try:
            email = re.search(r'Email(.+)\r', info_box).group(1)
        except AttributeError:
            email = None
        address = root.xpath('//nobr/text()')[0].replace(u'\xa0', ' ')
        leg.add_office('district', 'District Office', address=address,
                       phone=phone, email=email)

        try:
            leg['occupation'] = re.search(
                r'Occupation(.+)\r', info_box).group(1)
        except AttributeError:
            pass

        self.save_legislator(leg)
