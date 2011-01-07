import re

from scrapelib import Scraper
from BeautifulSoup import BeautifulSoup

SESSION_NAME_RE = re.compile(r'^(?P<year>\d{4}) (?P<sub_session>.*)$')

status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=False,
    votes=False,
    legislators=True,
    contributors=['Rishabh Manocha <rmanocha@gmail.com>'],
    notes="""
    Bills starting from 1996 can be scraped. However, only
    the current term's legislators (2010) are scraped.
    Votes for a given bill are provided in a pdf file hence
    they are not being collected (a document is added to each
    bill with relevant upper and lower house votes linking to 
    respective pdf files though). Also, all sponsors to a bill
    are added as primary sponsors (since the site does not tell
    us who is the primary sponsor and who is/are co-sponsors).""",
    )

metadata = {
    'state_name': 'New Mexico',
    'legislature_name': 'New Mexico Legislature',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_title': 'Senator',
    'lower_title': 'Representative',
    'upper_term': 4,
    'lower_term': 2,
    'sessions': [],
    'session_details': {
        }
    }

def get_session_details():
    """
    We will fetch a list of available sessions from the 'bill locator' page.
    We won't get legislators for all these sessions, but all bills for these
    sessions are available and we want to be able to get to them.
    """
    scraper = Scraper()

    nm_locator_url = 'http://legis.state.nm.us/lcs/locator.aspx'
    with scraper.urlopen(nm_locator_url) as page:
        page = BeautifulSoup(page)

        #The first `tr` is simply 'Bill Locator`. Ignoring that
        data_table = page.find('table', id = 'ctl00_mainCopy_Locators')('tr')[1:]
        for session in data_table:
            session_tag = session.find('a')
            session_name = ' '.join([tag.string.strip() for tag in session_tag('span')]).strip()

            session_year, sub_session_name = SESSION_NAME_RE.match(session_name).groups()
            if session_year in metadata['sessions']:
                if sub_session_name not in metadata['session_details'][session_year]['sub_sessions']:
                    metadata['session_details'][session_year]['sub_sessions'].append(sub_session_name)
            else:
                metadata['sessions'].append(session_year)
                metadata['session_details'][session_year] = dict(years = session_year, sub_sessions = [sub_session_name])

#get_session_details()
