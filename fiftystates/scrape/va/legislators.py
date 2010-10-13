from fiftystates.scrape.legislators import Legislator, LegislatorScraper

import re
import lxml.html

class VALegislatorScraper(LegislatorScraper):
    state = 'va'

    def scrape(self, chamber, term):
        abbr = {'upper': 'S', 'lower': 'H'}

        # TODO: figure out the best way to get all legislators for a term
        self.scrape_for_session(chamber, '2010', term)

    def scrape_for_session(self, chamber, session, term):
        site_id = self.metadata['session_details'][session]['site_id']
        url = 'http://leg6.state.va.us/%s/mbr/MBR.HTM' % site_id

        if chamber == 'lower':
            column = 'lColLt'
        elif chamber == 'upper':
            column = 'lColRt'

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            for link in doc.xpath('//div[@class="%s"]/ul/li/a' % column):
                self.fetch_member(link.get('href'), link.text, term, chamber)

    def fetch_member(self, url, name, term, chamber):
        party_map = {'R': 'Republican', 'D': 'Democratic', 'I': 'Independent'}
        party_district_re = re.compile(
            r'\((R|D|I)\) - (?:House|Senate) District\s+(\d+)')

        url = 'http://leg6.state.va.us' + url

        # handle resignations, special elections
        match = re.search(r'-(Resigned|Member) (\d{1,2}/\d{1,2})?', name)
        if match:
            action, date = match.groups()
            name = name.rsplit('-')[0]
            if action == 'Resigned':
                pass # TODO: set end date
            elif action == 'Member':
                pass # TODO: set start date

        with self.urlopen(url) as html:
            doc = lxml.html.fromstring(html)

            party_district_line = doc.xpath('//h3/font/text()')[0]
            party, district = party_district_re.match(party_district_line).groups()

            leg = Legislator(term, chamber, district, name.strip(),
                             party=party_map[party])
            leg.add_source(url)
            self.save_legislator(leg)
