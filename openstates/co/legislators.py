from billy.scrape import ScrapeError, NoDataForPeriod
from billy.scrape.legislators import LegislatorScraper, Legislator
from .utils import BASE_URL, year_from_session

import lxml.html
import re, contextlib

def legs_url(chamber):
    url = 'http://www.leg.state.co.us/Clics/CLICS2010A/directory.nsf/MIWeb?OpenForm&chamber='
    if chamber == 'upper':
        return url + 'Senate'
    else:
        return url + 'House'

def party_name(party_letter):
    if party_letter == 'D':
        return 'Republican'
    elif party_letter == 'R':
        return 'Democrat'
    else:
        return 'Independent'

def leg_form_url():
    return 'http://www.leg.state.co.us/clics/clics2010a/directory.nsf/d1325833be2cc8ec0725664900682205?SearchView'


class COLegislatorScraper(LegislatorScraper):
    state = 'co'

    def scrape(self, chamber, session):
        # Legislator data only available for the current session
        if year_from_session(session) != 2009:
            raise NoDataForPeriod(session)

        with self.urlopen(legs_url(chamber)) as html:
            page = lxml.html.fromstring(html)

            # Iterate through legislator names
            page.make_links_absolute(BASE_URL)
            for link in set([a.get('href') for a in page.xpath('//b/a')]):
                with self.urlopen(link) as legislator_html:
                    legislator_page = lxml.html.fromstring(legislator_html)

                    leg_elements = legislator_page.cssselect('b')
                    leg_name = leg_elements[0].text_content()

                    district = ""
                    district_match = re.search("District [0-9]+", legislator_page.text_content())
                    if (district_match != None):
                        district = district_match.group(0)

                    email = ""
                    email_match = re.search('E-mail: (.*)', legislator_page.text_content())
                    if (email_match != None):
                        email = email_match.group(1)

                    form_page = lxml.html.parse(leg_form_url()).getroot()
                    form_page.forms[0].fields['Query'] = leg_name
                    result = lxml.html.parse(lxml.html.submit_form(form_page.forms[0])).getroot()
                    elements = result.cssselect('td')
                    party_letter = elements[7].text_content()

                    party = party_name(party_letter)

                    leg = Legislator(session, chamber, district, leg_name,
                                 "", "", "", party,
                                 official_email=email)
                    leg.add_source(link)

                    self.save_legislator(leg)
