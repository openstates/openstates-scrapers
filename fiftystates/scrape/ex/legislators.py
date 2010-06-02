from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator


class EXLegislatorScraper(LegislatorScraper):
    state = 'ex'

    def scrape_legislators(self, chamber, year):
        if year != '2009':
            raise NoDataForYear

        l1 = Legislator('2009-2010', chamber, '1st',
                        'Bob Smith', party='Democrat')

        if chamber == 'upper':
            l1.add_role('President of the Senate', '2009-2010')
        else:
            l1.add_role('Speaker of the House', '2009-2010')

        l1.add_source('http://example.com/Bob_Smith.html')

        l2 = Legislator('2009-2010', chamber, '2nd',
                        'Sally Johnson', party='Republican')
        l2.add_role('Minority Leader', '2009-2010')
        l2.add_source('http://example.com/Sally_Johnson.html')

        self.save_legislator(l1)
        self.save_legislator(l2)
