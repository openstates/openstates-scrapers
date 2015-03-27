from billy.scrape.legislators import Legislator, LegislatorScraper

import re
import lxml.html


CHAMBER_MOVES = {
    "A. Benton \"Ben\" Chafin-Elect": "upper",
    "A. Benton Chafin-Senate Elect": "upper",
}


class VALegislatorScraper(LegislatorScraper):
    jurisdiction = 'va'

    def scrape(self, chamber, term):
        abbr = {'upper': 'S', 'lower': 'H'}

        sessions = []
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]

        self.scrape_for_session(chamber, session, term)

    def scrape_for_session(self, chamber, session, term):
        site_id = self.metadata['session_details'][session]['site_id']
        url = 'http://leg6.state.va.us/%s/mbr/MBR.HTM' % site_id

        if chamber == 'lower':
            column = 'lColLt'
        elif chamber == 'upper':
            column = 'lColRt'

        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for link in doc.xpath('//div[@class="%s"]/ul/li/a' % column):
            if 'resigned' in link.text:
                self.log('skipping %s' % link.text)
                continue
            self.fetch_member(link.get('href'), link.text, term, chamber)

    def fetch_member(self, url, name, term, chamber):
        if name in CHAMBER_MOVES:
            if chamber != CHAMBER_MOVES[name]:
                return  # Skip bad chambers.

        if "vacated" in name:
            return

        party_map = {'R': 'Republican', 'D': 'Democratic', 'I': 'Independent'}
        party_district_re = re.compile(
            r'\((R|D|I)\) - (?:House|Senate) District\s+(\d+)')

        # handle resignations, special elections
        match = re.search(r'-(Resigned|Member) (\d{1,2}/\d{1,2})?', name)
        if match:
            action, date = match.groups()
            name = name.rsplit('-')[0]

            if action == 'Resigned':
                pass # TODO: set end date
            elif action == 'Member':
                pass # TODO: set start date

        html = self.get(url).text
        doc = lxml.html.fromstring(html)

        party_district_line = doc.xpath('//h3/font/text()')[0]
        party, district = party_district_re.match(party_district_line).groups()

        leg = Legislator(term, chamber, district, name.strip(),
                         party=party_map[party], url=url)
        leg.add_source(url)

        for ul in doc.xpath('//ul[@class="linkNon"]'):
            address = []
            phone = None
            email = None
            for li in ul.getchildren():
                text = li.text_content()
                if re.match('\(\d{3}\)', text):
                    phone = text
                elif text.startswith('email:'):
                    email = text.strip('email: ').strip()
                else:
                    address.append(text)
                office_type = ('capitol' if 'Capitol Square' in address
                        else 'district')
                name = ('Capitol Office' if office_type == 'capitol'
                        else 'District Office')
            leg.add_office(office_type, name, address='\n'.join(address),
                           phone=phone, email=email)

        for com in doc.xpath('//ul[@class="linkSect"][1]/li/a/text()'):
            leg.add_role('committee member', term=term, chamber=chamber,
                         committee=com)

        self.save_legislator(leg)
