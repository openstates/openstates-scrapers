from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.ut import metadata

import lxml.html


class UTLegislatorScraper(LegislatorScraper):
    state = 'ut'

    def scrape(self, chamber, term):
        self.validate_term(term)

        year = term[0:4]

        lower_gone_2011 = set(["Ferry, Ben C.", "Hunsaker, Fred R",
                               "Gibson, Kerry W.", "Hansen, Neil A.",
                               "Wallis, C. Brent", "Aagard, Douglas C.",
                               "Allen, Sheryl L.", "Riesen, Phil",
                               "Black, Laura", "Mascaro, Steven R.",
                               "Beck, Trisha S.", "Seegmiller, F. Jay",
                               "Fowlke, Lorie D.", "Gowans, James R."])

        upper_gone_2011 = set(["Greiner, Jon J.", "Goodfellow, Brent H."])

        if chamber == 'lower':
            title = 'Representative'
        else:
            title = 'Senator'

        url = 'http://www.le.state.ut.us/asp/roster/roster.asp?year=%s' % year

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for row in page.xpath('//table[2]/tr')[1:]:
                row_title = row.xpath('string(td[2])')

                if row_title == title:
                    full_name = row.xpath('string(td[1])')
                    district = row.xpath('string(td[4])')
                    party = row.xpath('string(td[3])')

                    # The UT legislator list still shows incumbents that
                    # lost or retired (as of Jan 11 2011)
                    if term == '2011-2012':
                        if chamber == 'lower' and full_name in lower_gone_2011:
                            print "Skipping %s" % full_name
                            continue
                        elif chamber == 'upper' and full_name in upper_gone_2011:
                            print "Skipping %s" % full_name
                            continue

                    leg = Legislator(term, chamber, district,
                                     full_name, '', '', '',
                                     party)
                    leg.add_source(url)
                    self.save_legislator(leg)
