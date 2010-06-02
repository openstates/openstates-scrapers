import html5lib

from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nc.utils import split_name

class NCLegislatorScraper(LegislatorScraper):
    state = 'nc'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape_legislators(self, chamber, year):
        session = "%d-%d" % (int(year), int(year) + 1)

        url = "http://www.ncga.state.nc.us/gascripts/members/"\
            "memberList.pl?sChamber="

        if chamber == 'lower':
            url += 'House'
        else:
            url += 'Senate'

        with self.urlopen(url) as (resp, data):
            leg_list = self.soup_parser(data)
            leg_table = leg_list.find('div', id='mainBody').find('table')

            for row in leg_table.findAll('tr')[1:]:
                party = row.td.contents[0].strip()
                if party == 'Dem':
                    party = 'Democrat'
                elif party == 'Rep':
                    party = 'Republican'

                district = row.findAll('td')[1].contents[0].strip()
                full_name = row.findAll('td')[2].a.contents[0].strip()
                full_name = full_name.replace(u'\u00a0', ' ')
                (first_name, last_name, middle_name, suffix) = split_name(
                    full_name)

                legislator = Legislator(session, chamber, district, full_name,
                                        first_name, last_name, middle_name,
                                        party, suffix=suffix)
                legislator.add_source(url)
                self.save_legislator(legislator)
