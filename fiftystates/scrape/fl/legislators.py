import re

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.fl import metadata

from BeautifulSoup import BeautifulSoup


class FLLegislatorScraper(LegislatorScraper):
    state = 'fl'

    def scrape(self, chamber, year):
        for session in metadata['sessions']:
            if session['start_year'] <= int(year) <= session['end_year']:
                break
        else:
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_senators(year)
        else:
            self.scrape_reps(year)

    def scrape_senators(self, year):
        if year != '2009':
            return

        leg_page_url = "http://www.flsenate.gov/Legislators/"\
            "index.cfm?Mode=Member%20Pages&Submenu=1&Tab=legislators"
        leg_page = BeautifulSoup(self.urlopen(leg_page_url))

        th = leg_page.find('th', text='Legislator').parent
        table = th.parent.parent

        for row in table.findAll('tr')[1:]:
            full = row.td.a.contents[0].replace('  ', ' ')

            district = row.findAll('td')[1].contents[0]
            party = row.findAll('td')[2].contents[0]

            leg = Legislator(year, 'upper', district, full, party=party)
            leg.add_source(leg_page_url)
            self.save_legislator(leg)

    def scrape_reps(self, year):
        if year != '2009':
            return

        leg_page_url = "http://www.flhouse.gov/Sections/Representatives/"\
            "representatives.aspx"
        leg_page = BeautifulSoup(self.urlopen(leg_page_url))

        table = leg_page.find('table',
                              id='ctl00_ContentPlaceHolder1_ctrlContentBox'\
                                  '_ctrlPageContent_ctl00_dgLegislators')

        for row in table.findAll('tr')[1:]:
            full = row.findAll('td')[1].a.contents[0].replace('  ', ' ')

            district = row.findAll('td')[3].contents[0]
            party = row.findAll('td')[2].contents[0]

            if party == 'D':
                party = 'Democrat'
            elif party == 'R':
                party = 'Republican'

            leg = Legislator(year, 'lower', district, full, party=party)
            leg.add_source(leg_page_url)
            self.save_legislator(leg)
