import re
import lxml.html
from billy.utils.fulltext import text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=120)

metadata = dict(
    name='New York',
    abbreviation='ny',
    capitol_timezone='America/New_York',
    legislature_name='New York Legislature',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assembly Member'},
    },
    terms=[
        dict(name='2011-2012', start_year=2011, end_year=2012,
             sessions=['2011-2012']),
        dict(name='2013-2014', start_year=2013, end_year=2014,
             sessions=['2013-2014'])
        ],
    session_details={
        '2011-2012': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        },
        '2013-2014': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        }
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=['2009'],

    requests_per_minute=30,
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://open.nysenate.gov/legislation/advanced/',
                     '//select[@name="session"]/option/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    # if there's a header above a _________, ditch it
    text = text.rsplit('__________', 1)[-1]
    # strip numbers from lines (not all lines have numbers though)
    text = re.sub('\n\s*\d+\s*', ' ', text)
    return text
