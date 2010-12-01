from fiftystates.scrape import NoDataForPeriod
from fiftystates.scrape.legislators import LegislatorScraper, Legislator

import lxml.html


class VTLegislatorScraper(LegislatorScraper):
    state = 'vt'

    def scrape(self, chamber, term):
        if term != '2009-2010':
            raise NoDataForPeriod(term)

        # What Vermont claims are Word and Excel files are actually
        # just HTML tables
        # What Vermont claims is a CSV file is actually one row of comma
        # separated values followed by a ColdFusion error.
        url = ("http://www.leg.state.vt.us/legdir/"
               "memberdata.cfm/memberdata.doc?FileType=W")

        with self.urlopen(url) as page:
            page = lxml.html.fromstring(page)

            for tr in page.xpath("//tr")[1:]:
                row_chamber = tr.xpath("string(td[4])")
                if row_chamber == 'S' and chamber == 'lower':
                    continue
                elif row_chamber == 'H' and chamber == 'upper':
                    continue

                district = tr.xpath("string(td[6])")
                district = district.replace('District', '').strip()

                first_name = tr.xpath("string(td[7])")
                middle_name = tr.xpath("string(td[8])")
                last_name = tr.xpath("string(td[9])")

                if first_name.endswith(" %s." % middle_name):
                    first_name = first_name.split(" %s." % middle_name)[0]

                if middle_name:
                    full_name = "%s %s. %s" % (first_name, middle_name,
                                              last_name)
                else:
                    full_name = "%s %s" % (first_name, last_name)

                email = tr.xpath("string(td[10])")

                party = tr.xpath("string(td[5])")
                party = {'D': 'Democratic',
                         'R': 'Republican',
                         'I': 'Independent',
                         'P': 'Progressive',
                         'X': 'Progressive'}.get(party, party)

                leg = Legislator(term, chamber, district, full_name,
                                 first_name=first_name,
                                 middle_name=middle_name,
                                 last_name=last_name,
                                 party=party,
                                 email=email)
                leg.add_source(url)
                self.save_legislator(leg)
