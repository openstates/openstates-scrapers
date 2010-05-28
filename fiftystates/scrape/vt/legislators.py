from fiftystates.scrape.legislators import LegislatorScraper, Legislator

from BeautifulSoup import BeautifulSoup


class VTLegislatorScraper(LegislatorScraper):
    state = 'vt'

    def scrape_legislators(self, chamber, year):
        if int(year) != 2009:
            return
        session = "%s-%d" % (year, int(year) + 1)

        # What Vermont claims are Word and Excel files are actually
        # just HTML tables
        # What Vermont claims is a CSV file is actually one row of comma
        # separated values followed by a ColdFusion error.
        leg_url = "http://www.leg.state.vt.us/legdir/"\
            "memberdata.cfm/memberdata.doc?FileType=W"
        leg_table = BeautifulSoup(self.urlopen(leg_url))

        for tr in leg_table.findAll('tr')[1:]:
            leg_cham = tr.findAll('td')[3].contents[0]
            if leg_cham == 'H' and chamber == 'upper':
                continue
            if leg_cham == 'S' and chamber == 'lower':
                continue

            district = tr.findAll('td')[5].contents[0]
            district = district.replace(' District', '').strip()
            first = tr.findAll('td')[6].contents[0]

            middle = tr.findAll('td')[7]
            if len(middle.contents) == 0:
                middle = ''
            else:
                middle = middle.contents[0].strip()

            last = tr.findAll('td')[8].contents[0]

            if len(middle) == 0:
                full = "%s, %s" % (last, first)
            else:
                full = "%s, %s %s." % (last, first, middle)

            official_email = tr.findAll('td')[9]
            if len(official_email.contents) == 0:
                official_email = ''
            else:
                official_email = official_email.contents[0]

            party = tr.findAll('td')[4].contents[0]
            if party == 'D':
                party = 'Democrat'
            elif party == 'R':
                party = 'Republican'
            elif party == 'I':
                party = 'Independent'
            elif party == 'P':
                party = 'Progressive'

            leg = Legislator(session, chamber, district, full,
                             first, last, middle, party,
                             official_email=official_email)
            leg.add_source(leg_url)
            self.save_legislator(leg)
