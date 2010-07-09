import re
import datetime

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class LALegislatorScraper(LegislatorScraper):
    state = 'la'

    def scrape(self, chamber, year):
        if year != '2009':
            raise NoDataForYear(year)

        list_url = "http://www.legis.state.la.us/bios.htm"
        with self.urlopen(list_url) as text:
            page = lxml.html.fromstring(text)
            page.make_links_absolute(list_url)

            if chamber == 'upper':
                contains = 'senate.legis'
            else:
                contains = 'house.louisiana'

            for a in page.xpath("//a[contains(@href, '%s')]" % contains):
                name = a.text.strip()
                leg_url = a.attrib['href']
                if chamber == 'upper':
                    try:
                        self.scrape_senator(name, year, leg_url)
                    except Exception as e:
                        print e
                else:
                    self.scrape_rep(name, year, leg_url)

    def scrape_rep(self, name, term, url):
        # special case a name that confuses name_tools
        if name == 'Franklin, A.B.':
            name = 'Franklin, A. B.'

        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            district = page.xpath(
                "//a[contains(@href, 'Maps')]")[0].attrib['href']
            district = re.search("district(\d+).pdf", district).group(1)

            if "Democrat&nbsp;District" in text:
                party = "Democrat"
            elif "Republican&nbsp;District" in text:
                party = "Republican"
            else:
                party = "Other"

            leg = Legislator(session, 'lower', district, name, party=party)
            leg.add_source(url)
            self.save_legislator(leg)

    def scrape_senator(self, name, session, url):
        with self.urlopen(url) as text:
            page = lxml.html.fromstring(text)

            district = page.xpath(
                "string(//*[starts-with(text(), 'Senator ')])")

            district = re.search(r'District (\d+)', district).group(1)

            party = page.xpath(
                "//b[text() = 'Party']")[0].getnext().tail.strip()

            leg = Legislator(session, 'upper', district, name, party=party)
            leg.add_source(url)
            self.save_legislator(leg)
