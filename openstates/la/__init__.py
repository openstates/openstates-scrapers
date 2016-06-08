import datetime
import re
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import LABillScraper
from .legislators import LALegislatorScraper
from .committees import LACommitteeScraper
from .events import LAEventScraper

metadata = {
    'name': 'Louisiana',
    'abbreviation': 'la',
    'legislature_name': 'Louisiana Legislature',
    'legislature_url': 'http://www.legis.la.gov/',
    'capitol_timezone': 'America/Chicago',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    # Louisiana legislators serve four-year terms.
    'terms': [
        {
            'name': '2008-2011',
            'start_year': 2008,
            'end_year': 2011,
            'sessions': [
                '2009',
                '2010',
                '2011 1st Extraordinary Session',
                '2011',
            ],
        },
        {
            'name': '2012-2015',
            'start_year': 2012,
            'end_year': 2015,
            'sessions': [
                '2012',
                '2013',
                '2014',
                '2015',
            ],
        },
        {
            'name': '2016-2019',
            'start_year': 2016,
            'end_year': 2019,
            'sessions': [
                '2016',
                '2016 1st Extraordinary Session',
                '2016 2nd Extraordinary Session',
            ],
        },
    ],
    'session_details': {
        '2009': {
            'type': 'primary',
            'start_date': datetime.date(2010, 4, 27),
            'end_date': datetime.date(2010, 6, 24),
            'display_name': '2009 Regular Session',
            '_id': '09RS',
            '_scraped_name': '2009 Regular Session',
        },
        '2010': {
            'type': 'primary',
            'start_date': datetime.date(2010, 3, 29),
            'end_date': datetime.date(2010, 6, 21),
            'display_name': '2010 Regular Session',
            '_id': '10RS',
            '_scraped_name': '2010 Regular Session',
        },
        '2011 1st Extraordinary Session': {
            'type': 'special',
            'start_date': datetime.date(2011, 3, 20),
            'end_date': datetime.date(2011, 4, 13),
            'display_name': '2011, 1st Extraordinary Session',
            '_id': '111ES',
            '_scraped_name': '2011 First Extraordinary Session',
        },
        '2011': {
            'type': 'primary',
            'start_date': datetime.date(2011, 4, 25),
            'end_date': datetime.date(2011, 6, 23),
            'display_name': '2011 Regular Session',
            '_id': '11RS',
            '_scraped_name': '2011 Regular Session',
        },
        '2012': {
            'type': 'primary',
            'start_date': datetime.date(2012, 3, 12),
            'end_date': datetime.date(2012, 6, 4),
            'display_name': '2012 Regular Session',
            '_id': '12RS',
            '_scraped_name': '2012 Regular Session',
        },
        '2013': {
            'type': 'primary',
            'start_date': datetime.date(2013, 4, 8),
            'end_date': datetime.date(2013, 6, 6),
            'display_name': '2013 Regular Session',
            '_id': '13RS',
            '_scraped_name': '2013 Regular Session',
        },
        '2014': {
            'type': 'primary',
            'start_date': datetime.date(2014, 3, 10),
            'end_date': datetime.date(2014, 6, 2),
            'display_name': '2014 Regular Session',
            '_id': '14RS',
            '_scraped_name': '2014 Regular Session',
        },
        '2015': {
            'type': 'primary',
            'start_date': datetime.date(2015, 4, 13),
            'end_date': datetime.date(2015, 6, 11),
            'display_name': '2015 Regular Session',
            '_id': '15RS',
            '_scraped_name': '2015 Regular Session',
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016, 3, 14),
            'end_date': datetime.date(2016, 6, 6),
            'display_name': '2016 Regular Session',
            '_id': '16RS',
            '_scraped_name': '2016 Regular Session',
        },
        '2016 1st Extraordinary Session': {
            'type': 'special',
            'start_date': datetime.date(2016, 2, 14),
            'end_date': datetime.date(2016, 3, 9),
            'display_name': '2016, 1st Extraordinary Session',
            '_id': '161ES',
            '_scraped_name': '2016 First Extraordinary Session',
        },
        '2016 2nd Extraordinary Session': {
            'type': 'special',
            'start_date': datetime.date(2016, 6, 6),
            'end_date': datetime.date(2016, 6, 23),
            'display_name': '2016, 2nd Extraordinary Session',
            '_id': '162ES',
            '_scraped_name': '2016 Second Extraordinary Session',
        },
    },
    'feature_flags': ['subjects', 'influenceexplorer', 'events'],
    '_ignored_scraped_sessions': [
        '2016 Organizational Session',
        '2015 Regular Session',
        '2014 Regular Session',
        '2013 Regular Session',
        '2012 Regular Session',
        '2012 Organizational Session',
        '2011 Regular Session',
        '2011 First Extraordinary Session',
        '2010 Regular Session',
        '2009 Regular Session',
        '2008 Regular Session',
        '2008 Organizational Session',
        '2008 Second Extraordinary Session',
        '2008 First Extraordinary Session',
        '2007 Regular Session',
        '2006 Regular Session',
        '2005 Regular Session',
        '2004 Regular Session',
        '2004 First Extraordinary Session',
        '2004 1st Extraordinary Session',
        '2003 Regular Session',
        '2002 Regular Session',
        '2001 Regular Session',
        '2000 Regular Session',
        '1999 Regular Session',
        '1998 Regular Session',
        '1997 Regular Session',
        '2006 Second Extraordinary Session',
        '2006 First Extraordinary Session',
        '2005 First Extraordinary Session',
        '2002 First Extraordinary Session',
        '2001 Second Extraordinary Session',
        '2001 First Extraordinary Session',
        '2000 Second Extraordinary Session',
        '2000 First Extraordinary Session',
        '1998 First Extraordinary Session',
        '2012 Organizational Session',
        '2000 Organizational Session',
        '2004 Organizational Session',
        'Other Sessions',
        'Other Sessions',
        'Sessions',
    ]
}


def session_list():
    return url_xpath(
        'http://www.legis.la.gov/Legis/SessionInfo/SessionInfo.aspx',
        '//table[@id="ctl00_ctl00_PageBody_DataListSessions"]//a[contains'
        '(text(), "Session")]/text()')


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
