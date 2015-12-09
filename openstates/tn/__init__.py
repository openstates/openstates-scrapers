import re
import datetime
from billy.utils.fulltext import pdfdata_to_text
from .bills import TNBillScraper
from .legislators import TNLegislatorScraper
from .committees import TNCommitteeScraper
from .events import TNEventScraper

settings = dict(SCRAPELIB_TIMEOUT=600)

#start date of each session is the first tuesday in January after new years

metadata = dict(
    name='Tennessee',
    abbreviation='tn',
    capitol_timezone='America/Chicago',
    legislature_name='Tennessee General Assembly',
    legislature_url='http://www.legislature.state.tn.us/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '106', 'sessions': ['106'],
            'start_year': 2009, 'end_year': 2010},
        {'name': '107', 'sessions': ['107'],
            'start_year': 2011, 'end_year': 2012},
        {'name': '108', 'sessions': ['108'],
            'start_year': 2013, 'end_year': 2014},
        {'name': '109', 'sessions': ['109'],
            'start_year': 2015, 'end_year': 2016},
    ],
    session_details={
        '109': {
            'type': 'primary',
            'display_name': '109th Regular Session (2015-2016)',
            '_scraped_name': '109th General Assembly'},
        '108': {
            'type': 'primary',
            'display_name': '108th Regular Session (2013-2014)',
            '_scraped_name': '108th General Assembly'},
        '107': {
            'start_date': datetime.date(2011, 1, 11),
            'end_date': datetime.date(2012, 1, 10),
            'type': 'primary',
            'display_name': '107th Regular Session (2011-2012)',
            '_scraped_name': '107th General Assembly'},
        '106': {
            'type': 'primary',
            'display_name': '106th Regular Session (2009-2010)',
            '_scraped_name': '106th General Assembly'},
    },
    feature_flags=['events', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '107th General Assembly',
        '105th General Assembly', '104th General Assembly',
        '103rd General Assembly', '102nd General Assembly',
        '101st General Assembly', '100th General Assembly',
        '99th General Assembly'
    ]
)


def session_list():
    # Special sessions are available in the archive, but not in current session.
    # Solution is to scrape special session as part of regular session
    from billy.scrape.utils import url_xpath
    sessions = [
            x for x in 
            url_xpath('http://www.capitol.tn.gov/legislation/archives.html',
            '//h2[text()="Bills and Resolutions"]/following-sibling::ul/li/text()')
            if x.strip()
            ]
    sessions.append("109th General Assembly")
    return sessions


def extract_text(doc, data):
    return ' '.join(line for line in pdfdata_to_text(data).splitlines()
                    if re.findall('[a-z]', line)).decode('utf8')
