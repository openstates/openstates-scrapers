import re
import urlparse
import htmlentitydefs

from fiftystates.scrape import NoDataForYear
from fiftystates.scrape.legislators import LegislatorScraper, Legislator
from fiftystates.scrape.nj.utils import clean_committee_name

import lxml.etree
import urllib

class NJLegislatorScraper(LegislatorScraper):
    state = 'nj'

    def scrape(self, chamber, year):
        self.save_errors=False
        if year < 2009:
            raise NoDataForYear(year)

        if chamber == 'upper':
            self.scrape_legislators(chamber, year)
        elif chamber == 'lower':
            self.scrape_legislators(chamber, year)

    def scrape_legislators(self, chamber, year):

        leg_url = 'http://www.njleg.state.nj.us/members/roster_BIO.asp'
        body = 'SearchFirstName=&SearchLastName=&District=&SubmitSearch=Find&GotoPage=2&MoveRec=&Search=Search&ClearSearch=&GoTo=2'

        with self.urlopen(leg_url, 'POST', body) as page:
            root = lxml.etree.fromstring(page, lxml.etree.HTMLParser())
            session = year
            save_district = '' 
            for mr in root.xpath('//table/tr[4]/td/table/tr'):
                full_name = mr.xpath('string(td[2]/a)')
                full_name = self.unescape(full_name)
                full_name = full_name.replace('u00a0', ' ')
                #print name
                info = mr.xpath('string(td[2])').split()
                party = ''
                chamber = ''
                if 'Democrat' in info:
                    party = 'Democrat'
                elif 'Republican' in info:
                    party = 'Republican'
                if ('Assemblywoman' in info) or ('Assemblyman' in info):
                    chamber = 'General Assembly'
                elif 'Senator' in info:
                    chamber = 'Senate'

                if len(chamber) > 0:
                    leg = Legislator(session, chamber, save_district, full_name, "", "", "", party)
                    leg.add_source(leg_url)
                    self.save_legislator(leg)

                district = mr.xpath('string(td/a/font/b)').split()
                if len(district) > 0:
                    district = district[0] + " " + district[1]
                    save_district = district


    ## From Coleslaw
    # Removes HTML or XML character references and entities from a text string.
    #
    # @param text The HTML (or XML) source text.
    # @return The plain text, as a Unicode string, if necessary.
    def unescape(self, text):
        def fixup(self, m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)


