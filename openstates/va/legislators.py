import re
import lxml.html
from billy.scrape.legislators import Legislator, LegislatorScraper
from openstates.utils import LXMLMixin

CHAMBER_MOVES = {
    "A. Benton \"Ben\" Chafin-Elect": "upper",
    "A. Benton Chafin-Senate Elect": "upper",
}


class VALegislatorScraper(LegislatorScraper, LXMLMixin):
    jurisdiction = 'va'

    def _get_lis_id(self, chamber, url):
        """Retrieves LIS ID of legislator from URL."""
        if chamber == 'lower':
            regex = r'(H[0-9]+$)'
        elif chamber == 'upper':
            regex = r'(S[0-9]+$)'
        else:
            raise ValueError('Invalid chamber: {}'.format(chamber))

        match = re.search(regex, url)

        if match.groups:
            lis_id = match.group(1)
        else:
            lis_id = None

        return lis_id

    def scrape(self, chamber, term):
        sessions = []
        for t in self.metadata['terms']:
            if t['name'] == term:
                session = t['sessions'][-1]

        self.scrape_for_session(chamber, session, term)

    def scrape_for_session(self, chamber, session, term):
        site_id = self.metadata['session_details'][session]['site_id']
        url = 'http://lis.virginia.gov/%s/mbr/MBR.HTM' % site_id

        if chamber == 'lower':
            column = 'lColLt'
        elif chamber == 'upper':
            column = 'lColRt'

        doc = self.lxmlize(url)

        for link in doc.xpath('//div[@class="%s"]/ul/li/a' % column):
            if 'resigned' in link.text:
                self.log('skipping %s' % link.text)
                continue
            
            self.fetch_member(link.get('href'), link.text, term, chamber)

    def fetch_member(self, url, name, term, chamber):
        photo_url = ''

        lis_id = self._get_lis_id(chamber, url)

        if chamber == 'lower':
            base_url = 'http://memdata.virginiageneralassembly.gov'
            profile_url = base_url + '/images/display_image/{}'
            photo_url = profile_url.format(lis_id)
            #xpath_query = './/img/@src'
        elif chamber == 'upper':
            base_url = 'http://apps.senate.virginia.gov'
            profile_url = base_url + '/Senator/memberpage.php?id={}'
            xpath_query = './/img[@class="profile_pic"]/@src'

            # Retrieve profile photo.
            profile_page = self.lxmlize(profile_url.format(lis_id))
            photo_url = self.get_node(
                profile_page,
                xpath_query)

        # Detect whether URL points to a blank base location.
        blank_urls = (
            'http://memdata.virginiageneralassembly.gov/images/display_'
            'image/',
            'http://virginiageneralassembly.gov/house/members/photos/',
        )

        if photo_url in blank_urls:
            photo_url = ''

        if (name in CHAMBER_MOVES and(chamber != CHAMBER_MOVES[name])):
            return

        if "vacated" in name.lower():
            self.logger.warning("Seat seems to have been vacated: '{}'".format(name))
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

        # Scrub status from name.
        name = re.sub(r'(- Elect)$', '', name).strip()

        leg = Legislator(
            term=term,
            chamber=chamber,
            district=district,
            full_name=name.strip(),
            party=party_map[party],
            url=url,
            photo_url=photo_url,
        )
        leg.add_source(url)

        for ul in doc.xpath('//ul[@class="linkNon" and normalize-space()]'):
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
