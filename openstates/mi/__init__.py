import lxml.html
from billy.utils.fulltext import text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=600)

metadata = {
    'name': 'Michigan',
    'abbreviation': 'mi',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Michigan Legislature',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012},
    ],
    'session_details': {
        '2011-2012': {'type':'primary',
                      'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-2012',
                     },
    },
    'feature_flags': ['subjects', 'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2009-2010', '2007-2008', '2005-2006',
                                  '2003-2004', '2001-2002', '1999-2000',
                                  '1997-1998', '1995-1996']

}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legislature.mi.gov/mileg.aspx?'
                     'page=LegBasicSearch', '//option/text()')


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//body')[0].text_content()
    return text
