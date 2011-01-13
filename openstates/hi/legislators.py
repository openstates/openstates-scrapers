from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from openstates.hi.utils import year_from_session, BASE_URL

import lxml.html

import itertools

# From the itertools docs's recipe section 
def grouper(n, iterable, fillvalue=None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.izip_longest(fillvalue=fillvalue, *args) 


class HILegislatorScraper(LegislatorScraper):
    state = 'hi'

    def scrape(self, chamber, session):
        # All other years are stored in a pdf
        # http://www.capitol.hawaii.gov/session2009/misc/statehood.pdf
        if year_from_session(session) != 2009:
            raise NoDataForPeriod(session)

        if chamber == 'upper':
            legislators_page_url = BASE_URL + "/site1/info/direct/sendir.asp"
        else:
            legislators_page_url = BASE_URL + "/site1/info/direct/repdir.asp"

        with self.urlopen(legislators_page_url) as legislators_page_html:
            legislators_page = lxml.html.fromstring(legislators_page_html)

            # get all rows (except first) of first table
            legislators_data = legislators_page.xpath('//table[1]/tr')[1:]
            # group legislator data in sets of 3
            legislators_data = grouper(3, legislators_data)

            for name_and_party, district, email in legislators_data:
                element, attribute, link, pos = name_and_party.iterlinks().next()
                source = BASE_URL + link

                name_and_party = name_and_party.cssselect('td')
                name_and_party = name_and_party[0]
                name, sep, party =  name_and_party.text_content().partition("(")
                # remove space at the beginning
                name = name.strip()

                if party == 'R)':
                    party = 'Republican'
                else:
                    party = 'Democratic'

                district = district.cssselect('td')
                district = district[1]
                district = district.text_content()

                email = email.cssselect('a')
                email = email[0]
                email = email.text_content()
                # Remove white space
                email = email.strip()

                leg = Legislator(session, chamber, district, name,
                                 party=party, official_email=email)
                leg.add_source(source)
                self.save_legislator(leg)
