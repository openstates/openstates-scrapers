from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator


class EXLegislatorScraper(LegislatorScraper):
    state = 'ex'

    def scrape(self, chamber, term):
        self.validate_term(term)

        l1 = Legislator(term, chamber, '1st',
                        'Bob Smith', party='Democrat')

        if chamber == 'upper':
            l1.add_role('President of the Senate', term)
        else:
            l1.add_role('Speaker of the House', term)

        l1.add_source('http://example.com/Bob_Smith.html')

        l2 = Legislator(term, chamber, '2nd',
                        'Sally Johnson', party='Republican')
        l2.add_role('Minority Leader', term)
        l2.add_source('http://example.com/Sally_Johnson.html')

        self.save_legislator(l1)
        self.save_legislator(l2)
