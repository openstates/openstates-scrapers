import re
from collections import defaultdict

from billy.utils import urlescape
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class WVLegislatorScraper(LegislatorScraper):
    jurisdiction = 'wv'

    def scrape(self, chamber, term):
        self.validate_term(term, latest_only=True)

        if chamber == 'upper':
            chamber_abbrev = 'Senate1'
        else:
            chamber_abbrev = 'House'

        url = 'http://www.legis.state.wv.us/%s/roster.cfm' % chamber_abbrev
        page = lxml.html.fromstring(self.get(url).text)
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, '?member=')]"):
            if not link.text:
                continue
            name = link.xpath("string()").strip()
            leg_url = urlescape(link.attrib['href'])

            if name in ['Members', 'Senate Members', 'House Members',
                'Vacancy', 'VACANT', 'Vacant', 'To Be Announced',
                'To Be Appointed']:
                continue

            self.scrape_legislator(chamber, term, name, leg_url)

    def scrape_legislator(self, chamber, term, name, url):
        html = self.get(url).text
        page = lxml.html.fromstring(html)
        page.make_links_absolute(url)

        xpath = '//select[@name="sel_member"]/option[@selected]/text()'
        district = page.xpath('//h1[contains(., "DISTRICT")]/text()').pop().split()[1].strip().lstrip('0')

        party = page.xpath('//h2').pop().text_content()
        party = re.search(r'\((R|D)[ \-\]]', party).group(1)

        if party == 'D':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'

        photo_url = page.xpath(
            "//img[contains(@src, 'images/members/')]")[0].attrib['src']


        leg = Legislator(term, chamber, district, name, party=party,
                         photo_url=photo_url, url=url)
        leg.add_source(url)
        self.scrape_offices(leg, page)
        self.save_legislator(leg)

    def scrape_offices(self, legislator, doc):
        # Retrieve element that should contain all contact information for the
        # legislator and turn its text into a list.
        text = doc.xpath('//b[contains(., "Capitol Office:")]')[0]
        text = text.getparent().itertext()
        text = filter(None, [t.strip() for t in text])

        # Parse capitol office contact details.
        officedata = defaultdict(list)
        current = None
        for chunk in text:
            # Skip parsing biography link.
            if chunk.lower() == 'biography':
                break
            # Contact snippets should be elements with headers that end in
            # colons.
            if chunk.strip().endswith(':'):
                current_key = chunk.strip()
                current = officedata[current_key]
            elif current is not None:
                current.append(chunk)
                if current_key == 'Business Phone:':
                    break

        email = doc.xpath('//a[contains(@href, "mailto:")]/@href')[1]
        email = email[7:]

        try:
            if officedata['Capitol Phone:'][0] not in ('', 'NA'):
                capitol_phone = officedata['Capitol Phone:'][0]
            else:
                raise ValueError('Invalid phone number')
        except (IndexError, ValueError) as e:
            capitol_phone = None

        if officedata['Capitol Office:']:
            capitol_address = '\n'.join(officedata['Capitol Office:'])
        else:
            capitol_address = None

        capitol = dict(
            name='Capitol Office',
            type='capitol',
            phone=capitol_phone,
            fax=None,
            email=email,
            address=capitol_address,
        )

        legislator.add_office(**capitol)

        # If a business or home phone is listed, attempt to use the
        # home phone first, then fall back on the business phone for
        # the district office number.
        try:
            if officedata['Home Phone:'][0] not in ('', 'NA'):
                district_phone = officedata['Home Phone:'][0]
            elif officedata['Business Phone:'][0] not in ('', 'NA'):
                district_phone = officedata['Business Phone:'][0]
            else:
                raise ValueError('Invalid phone number')
        except (IndexError, ValueError) as e:
            district_phone = None

        if officedata['Home:']:
            district_address = '\n'.join(officedata['Home:'])
        else:
            district_address = None

        # Add district office entry only if data exists for it.
        if district_phone or officedata['Home:']:
            district = dict(
                name='District Office',
                type='district',
                phone=district_phone,
                address=district_address,
            )

            legislator.add_office(**district)
