import re
import datetime as dt
from htmlentitydefs import name2codepoint

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import html5lib
from BeautifulSoup import BeautifulSoup


class LALegislatorScraper(LegislatorScraper):
    state = 'la'

    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape(self, chamber, year):
        year = int(year)
        # we can scrape past legislator's from the main session page,
        # but we don't know what party they were..
        #http://house.louisiana.gov/H_Reps/members.asp?ID=
        #http://senate.legis.state.la.us/Senators/ByDistrict.asp
        if year != dt.date.today().year and year != dt.date.today().year - 1:
            raise NoDataForYear(year)
        if chamber == 'upper':
            self.scrape_upper_house(year)
        else:
            self.scrape_lower_house(year)
        pass

    def scrape_upper_house(self, year):
        senator_url = 'http://senate.legis.state.la.us/Senators/ByDistrict.asp'
        with self.urlopen(senator_url) as senator_page:
            senator_page = BeautifulSoup(senator_page)
            for senator in senator_page.findAll('td',
                                                width=355)[0].findAll('tr'):

                link = senator.findAll('a', text=re.compile("Senator"))
                if link != []:
                    leg_url = 'http://senate.legis.state.la.us%s' % (
                        link[0].parent['href'])

                    with self.urlopen(leg_url) as legislator_text:
                        legislator = self.soup_parser(legislator_text)
                        aleg = self.unescape(unicode(legislator))

                        #Senator A.G.  Crowe &nbsp; -&nbsp; District 1
                        name = re.findall(
                            r'Senator ([\w\s\.\,\"\-]+)\s*\-\s*District',
                            aleg)[0].strip()

                        name = name.replace('  ', ' ')
                        district = re.findall(r'\s*District (\d+)', aleg)[0]

                        parties = re.findall(
                            r'<b>Party<\/b><br \/>\s*(\w+)\s*<', aleg)
                        party = ', '.join(parties)

                        leg = Legislator(str(year), 'upper',
                                         str(district), name, party=party)

                        self.save_legislator(leg)

    def scrape_lower_house(self, year):
        #todo: tedious name parsing
        for i in range(1, 106):
            leg_url = "http://house.louisiana.gov/H_Reps/members.asp?ID=%d" % i

            with self.urlopen(leg_url) as legislator:
                legislator = BeautifulSoup(legislator)
                aleg = self.unescape(unicode(legislator))

                name = re.findall(
                    r'Representative ([\w\s\.\,\"\-\']+)\s*<br',
                    aleg)[0].strip()

                party, district = re.findall(
                    r'(\w+)\s*District\s*(\d+)', aleg)[0]

                leg = Legislator(str(year), 'lower', str(district),
                                 name, party=party)

                self.save_legislator(leg)

    def unescape(self, s):
        return re.sub('&(%s);' % '|'.join(name2codepoint),
                      lambda m: unichr(name2codepoint[m.group(1)]),
                      s).encode('ascii', 'ignore')
