import lxml.html
from billy.utils.fulltext import text_after_line_numbers
from .bills import MIBillScraper
from .legislators import MILegislatorScraper
from .committees import MICommitteeScraper
from .events import MIEventScraper

settings = dict(SCRAPELIB_TIMEOUT=600)

metadata = {
    'name': 'Michigan',
    'abbreviation': 'mi',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Michigan Legislature',
    'legislature_url': 'http://www.legislature.mi.gov',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['2013-2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['2015-2016'],
         'start_year': 2015, 'end_year': 2016},
    ],
    'session_details': {
        '2011-2012': {'type':'primary',
                      'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-2012',
                     },
        '2013-2014': {'type':'primary',
                      'display_name': '2013-2014 Regular Session',
                      '_scraped_name': '2013-2014',
                     },
        '2015-2016': {'type':'primary',
                      'display_name': '2015-2016 Regular Session',
                      '_scraped_name': '2015-2016',
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
