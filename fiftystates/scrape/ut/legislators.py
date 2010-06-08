from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ut import metadata

import html5lib


class UTLegislatorScraper(LegislatorScraper):
    state = 'ut'
    soup_parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('beautifulsoup')).parse

    def scrape(self, chamber, year):
        found = False
        for session in metadata['sessions']:
            if session['name'] == year:
                found = True
                break
        if not found:
            raise NoDataForYear(year)

        if chamber == 'lower':
            title = 'Representative'
        else:
            title = 'Senator'

        url = 'http://www.le.state.ut.us/asp/roster/roster.asp?year=%s' % year
        leg_list = self.soup_parser(self.urlopen(url))

        for row in leg_list.findAll('table')[1].findAll('tr')[1:]:
            tds = row.findAll('td')

            leg_title = tds[1].find(text=True)
            if leg_title == title:
                fullname = tds[0].find(text=True)
                last_name = fullname.split(',')[0]
                first_name = fullname.split(' ')[1]
                if len(fullname.split(' ')) > 2:
                    middle_name = fullname.split(' ')[2]

                leg = Legislator(year, chamber, tds[3].find(text=True),
                                 fullname, first_name, last_name,
                                 middle_name, tds[2].find(text=True))
                leg.add_source(url)
                self.save_legislator(leg)
