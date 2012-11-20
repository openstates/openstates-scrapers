import datetime
import lxml.html
from billy.utils.fulltext import text_after_line_numbers

metadata = dict(
    name='Ohio',
    abbreviation='oh',
    capitol_timezone='America/New_York',
    legislature_name='Ohio Legislature',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'sessions': ['128'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['129'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '128': { 'display_name': '128th Legislature',
                '_scraped_name': '128',
               },
        '129': {'start_date': datetime.date(2011, 1, 3),
                'display_name': '129th Legislature',
                '_scraped_name': '129',
               },
    },
    feature_flags=[ 'events', 'influenceexplorer' ],
    _ignored_scraped_sessions=['127', '126', '125', '124', '123', '122']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legislature.state.oh.us/search.cfm',
                     '//form[@action="bill_search.cfm"]//input[@type="radio" and @name="SESSION"]/@value')


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@align="LEFT"]'))
    return text
