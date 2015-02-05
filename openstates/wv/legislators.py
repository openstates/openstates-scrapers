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
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        for link in page.xpath("//a[contains(@href, '?member=')]"):
            if not link.text:
                continue
            name = link.xpath("string()").strip()
            leg_url = urlescape(link.attrib['href'])

            if name in ['Members', 'Senate Members', 'House Members',
                        'Vacancy', 'VACANT', 'Vacant', "To Be Announced"]:
                continue

            self.scrape_legislator(chamber, term, name, leg_url)

    def scrape_legislator(self, chamber, term, name, url):
        html = self.urlopen(url)
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
        email = doc.xpath(
            "//a[contains(@href, 'mailto:')]")[1].attrib['href'].split(
            'mailto:')[1]
        text = doc.xpath('//b[contains(., "Capitol Office:")]')[0]
        text = text.getparent().itertext()
        text = filter(None, [t.strip() for t in text])
        officedata = defaultdict(list)
        current = None
        for chunk in text:
            if chunk.lower() == 'biography':
                break
            if chunk.strip().endswith(':'):
                current_key = chunk.strip()
                current = officedata[current_key]
            elif current is not None:
                current.append(chunk)
                if current_key == 'Business Phone:':
                    break

        email = doc.xpath('//a[contains(@href, "mailto:")]/@href')[1]
        email = email[7:]

        office = dict(
            name='Capitol Office',
            type='capitol',
            phone=officedata['Capitol Phone:'][0] if officedata['Capitol Phone:'][0] not in ('', 'NA') else '',
            fax=None,
            email=email,
            address='\n'.join(officedata['Capitol Office:']))

        legislator.add_office(**office)

        if officedata.get('Business Phone:', '') not in ([], ['NA']):
            legislator.add_office(
                name='Business Office',
                type='district',
                phone=officedata['Business Phone:'][0])
