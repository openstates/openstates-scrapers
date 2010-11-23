import re
import datetime

from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class AKLegislatorScraper(LegislatorScraper):
    state = 'ak'

    def scrape(self, chamber, term):
        if term != '26':
            raise NoDataForPeriod(term)

        if chamber == 'upper':
            chamber_abbr = 'S'
            url = 'http://senate.legis.state.ak.us/'
            search = 'senator'
        else:
            chamber_abbr = 'H'
            url = 'http://house.legis.state.ak.us/'
            search = 'rep'

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)
            page.make_links_absolute(url)

            seen = set()
            for link in page.xpath("//a[contains(@href, '%s')]" % search):
                name = link.text

                # Members of the leadership are linked twice three times:
                # one image link and two text links. Don't double/triple
                # scrape them
                if not name or link.attrib['href'] in seen:
                    continue
                seen.add(link.attrib['href'])

                self.scrape_legislator(chamber, term,
                                       link.xpath('string()').strip(),
                                       link.attrib['href'])

    def scrape_legislator(self, chamber, term, name, url):
        with self.urlopen(url) as page:
            # Alaska fails at unicode, some of the pages have broken
            # characters. They're not in data we care about so just
            # replace them.
            page = page.decode('utf8', 'replace')
            page = lxml.html.fromstring(page)

            name = re.sub(r'\s+', ' ', name)

            info = page.xpath('string(//div[@id = "fullpage"])')

            district = re.search(r'District ([\w\d]+)', info).group(1)
            party = re.search(r'Party: (.+) Toll-Free', info).group(1).strip()

            leg = Legislator(term, chamber, district, name, party=party)
            leg.add_source(url)

            self.save_legislator(leg)
