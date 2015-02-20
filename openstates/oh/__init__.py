import datetime
import lxml.html
from billy.utils.fulltext import text_after_line_numbers
from .bills import OHBillScraper
from .legislators import OHLegislatorScraper
from .events import OHEventScraper

metadata = dict(
    name='Ohio',
    abbreviation='oh',
    capitol_timezone='America/New_York',
    legislature_name='Ohio General Assembly',
    legislature_url='http://www.legislature.state.oh.us/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'sessions': ['128'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['129'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['130'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['131'],
         'start_year': 2015, 'end_year': 2016},
    ],
    session_details={
        '128': { 'display_name': '128th Legislature (2009-2010)',
                '_scraped_name': '128',
               },
        '129': {'start_date': datetime.date(2011, 1, 3),
                'display_name': '129th Legislature (2011-2012)',
                '_scraped_name': '129',
               },
        '130': { 'display_name': '130th Legislature (2013-2014)',
                '_scraped_name': '130',
               },
        '131': { 'display_name': '131st Legislature (2015-2016)',
                '_scraped_name': '131',
               },
    },
    feature_flags=['influenceexplorer', 'events'],
    _ignored_scraped_sessions=['127', '126', '125', '124', '123', '122']

)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://archives.legislature.state.oh.us',
                     '//form[@action="bill_search.cfm"]//input[@type="radio" and @name="SESSION"]/@value')
    # Archive does not include current session
    sessions.append('131')
    return sessions


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@align="LEFT"]'))
    return text
