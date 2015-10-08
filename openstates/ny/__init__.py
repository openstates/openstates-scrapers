import re
import lxml.html
from billy.utils.fulltext import text_after_line_numbers
from .bills import NYBillScraper
from .legislators import NYLegislatorScraper
from .committees import NYCommitteeScraper
from .events import NYEventScraper

settings = dict(SCRAPELIB_TIMEOUT=120)

metadata = dict(
    name='New York',
    abbreviation='ny',
    capitol_timezone='America/New_York',
    legislature_name='New York Legislature',

    # unfortunate - there isn't a decent combined site
    legislature_url='http://public.leginfo.state.ny.us/',

    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assembly Member'},
    },
    terms=[
        dict(name='2009-2010', start_year=2010, end_year=2011,
             sessions=['2009-2010']),
        dict(name='2011-2012', start_year=2011, end_year=2012,
             sessions=['2011-2012']),
        dict(name='2013-2014', start_year=2013, end_year=2014,
             sessions=['2013-2014']),
        dict(name='2015-2016', start_year=2015, end_year=2016,
             sessions=['2015-2016'])
        ],
    session_details={
        '2009-2010': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009',
        },
        '2011-2012': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        },
        '2013-2014': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        },
        '2015-2016': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015',
        }
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=['2009'],

    requests_per_minute=30,
)

def session_list():
    from billy.scrape.utils import url_xpath
    url = 'http://nysenate.gov/search/legislation'
    sessions = url_xpath(url,
        '//select[@name="bill_session_year"]/option[@value!=""]/@value')
    return sessions

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    # if there's a header above a _________, ditch it
    text = text.rsplit('__________', 1)[-1]
    # strip numbers from lines (not all lines have numbers though)
    text = re.sub('\n\s*\d+\s*', ' ', text)
    return text
