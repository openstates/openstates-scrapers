import re

from billy.scrape import NoDataForPeriod
from billy.utils import urlescape
from billy.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class WVLegislatorScraper(LegislatorScraper):
    state = 'wv'

    def scrape(self, chamber, term):
        if term != '2011-2012':
            raise NoDataForPeriod(term)

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
                        'Vacancy']:
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

        leg = Legislator(term, chamber, district, name, party=party,
                         photo_url=photo_url)
        leg.add_source(url)
        self.save_legislator(leg)
