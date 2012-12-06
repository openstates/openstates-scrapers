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
            chamber_abbrev = 'sen'
            title_abbrev = 'sen'
        else:
            chamber_abbrev = 'hse'
            title_abbrev = 'del'

        url = "http://www.legis.state.wv.us/districts/maps/%s_dist.cfm" % (
            chamber_abbrev)
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        view_url = '%smemview' % title_abbrev
        for link in page.xpath("//a[contains(@href, '%s')]" % view_url):
            name = link.xpath("string()").strip()
            leg_url = urlescape(link.attrib['href'])

            if name in ['Members', 'Senate Members', 'House Members',
                        'Vacancy', 'VACANT']:
                continue

            self.scrape_legislator(chamber, term, name, leg_url)

    def scrape_legislator(self, chamber, term, name, url):
        page = lxml.html.fromstring(self.urlopen(url))
        page.make_links_absolute(url)

        dist_link = page.xpath("//a[contains(@href, 'dist=')]")[0]
        district = dist_link.xpath('string()').strip().lstrip('0')

        mem_span = page.xpath("//span[contains(@class, 'memname')]")[0]
        mem_tail = mem_span.tail.strip()

        party = re.match(r'\((R|D)', mem_tail).group(1)
        if party == 'D':
            party = 'Democratic'
        elif party == 'R':
            party = 'Republican'

        photo_url = page.xpath(
            "//img[contains(@src, 'images/members/')]")[0].attrib['src']

        email = page.xpath(
            "//a[contains(@href, 'mailto:')]")[1].attrib['href'].split(
            'mailto:')[1]

        leg = Legislator(term, chamber, district, name, party=party,
                         photo_url=photo_url, email=email, url=url)
        leg.add_source(url)

        for link in page.xpath("//a[contains(@href, 'committee.cfm')]"):
            comm = link.xpath("string()").strip()

            committee_chamber = chamber
            if 'interims' in link.attrib['href']:
                committee_chamber = 'joint'

            sub_index = comm.find('Subcommittee')
            if sub_index > 0:
                sub = comm[sub_index:].strip()
                comm = comm[:sub_index].strip()
                leg.add_role('committee member', term, committee=comm,
                             subcommittee=sub, chamber=committee_chamber)
            else:
                leg.add_role('committee member', term, committee=comm,
                             chamber=committee_chamber)

        self.scrape_offices(leg, page)
        self.save_legislator(leg)

    def scrape_offices(self, legislator, doc):
        text = doc.xpath('//b[contains(., "Capitol Address:")]')[0]
        text = text.getparent().itertext()
        text = filter(None, [t.strip() for t in text])
        officedata = defaultdict(list)
        current = None
        for chunk in text:
            if chunk.strip().endswith(':'):
                current = officedata[chunk.strip()]
            elif current is not None:
                current.append(chunk)

        office = dict(
            name='Capitol Office',
            type='capitol',
            phone=officedata['Capitol Phone:'].pop(),
            fax=None,
            email=officedata['E-mail:'].pop(),
            address='\n'.join(officedata['Capitol Address:']))

        legislator.add_office(**office)

        if officedata['Business Phone:']:
            legislator.add_office(
                name='Business Office',
                type='district',
                phone=officedata['Business Phone:'].pop())

