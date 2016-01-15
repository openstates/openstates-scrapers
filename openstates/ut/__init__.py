import datetime
import re
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from billy.scrape.utils import url_xpath
from .bills import UTBillScraper
from .legislators import UTLegislatorScraper
from .committees import UTCommitteeScraper
from .events import UTEventScraper

metadata = {
    'name': 'Utah',
    'abbreviation': 'ut',
    'legislature_name': 'Utah State Legislature',
    'legislature_url': 'http://le.utah.gov/',
    'capitol_timezone': 'America/Denver',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011', '2011S1', '2011S2', '2011S3', '2012',
                '2012S4'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2013h1', '2013s1', '2013s2', '2014'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015', '2015s1', '2016'],
        },
    ],
    'session_details': {
        '2011': {
            'type': 'primary',
            'start_date': datetime.date(2011, 1, 24),
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 General Session',
        },
        '2011S1': {
            'type': 'special',
            'display_name': '2011, 1st Special Session',
            '_scraped_name': '2011 1st Special Session',
        },
        '2011S2': {
            'type': 'special',
            'display_name': '2011, 2nd Special Session',
            '_scraped_name': '2011 2nd Special Session',
        },
        '2011S3': {
            'type': 'special',
            'display_name': '2011, 3rd Special Session',
            '_scraped_name': '2011 3rd Special Session',
        },
        '2012': {
            'type': 'primary',
            'display_name': '2012 General Session',
            '_scraped_name': '2012 General Session',
        },
        '2012S4': {
            'type': 'special',
            'display_name': '2012, 4th Special Session',
            '_scraped_name': '2012 4th Special Session',
        },
        '2013': {
            'type': 'primary',
            'display_name': '2013 General Session',
            '_scraped_name': '2013 General Session',
        },
        '2013h1': {
            'type': 'special',
            'display_name': '2013 House Session',
            '_scraped_name': '2013 House Session',
        },
        '2013s1': {
            'type': 'special',
            'display_name': '2013 1st Special Session',
            '_scraped_name': '2013 1st Special Session',
        },
        '2013s2': {
            'type': 'special',
            'display_name': '2013 2nd Special Session',
            '_scraped_name': '2013 2nd Special Session',
        },
        '2014': {
            'type': 'primary',
            'display_name': '2014 General Session',
            '_scraped_name': '2014 General Session',
        },
        '2015': {
            'type': 'primary',
            'display_name': '2015 General Session',
            '_scraped_name': '2015 General Session',
        },
        '2015s1': {
            'type': 'special',
            'display_name': '2015 1st Special Session',
            '_scraped_name': '2015 1st Special Session',
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016, 1, 25),
            'display_name': '2016 General Session',
            '_scraped_name': '2016 General Session',
        }
    },
    'feature_flags': ['events', 'subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2011 Veto Override Session',
        '2010 2nd Special Session',
        '2010 General Session',
        '2009 1st Special Session',
        '2009 General Session',
        '2008 2nd Special Session',
        '2008 General Session',
        '2007 1st Special Session',
        '2007 General Session',
        '2006 5th Special Session',
        '2006 4th Special Session',
        '2006 3rd Special Session',
        '2006 General Session',
        '2005 2nd Special Session',
        '2005 1st Special Session',
        '2005 General Session',
        '2004 4th Special Session',
        '2004 3rd Special Session',
        '2004 General Session',
        '2003 2nd Special Session',
        '2003 1st Special Session',
        '2003 General Session',
        '2002 Veto Override Session',
        '2002 6th Special Session',
        '2002 5th Special Session',
        '2002 4th Special Session',
        '2002 3rd Special Session',
        '2002 General Session',
        '2001 2nd Special Session',
        '2001 1st Special Session',
        '2001 General Session',
        '2000 General Session',
        '1999 General Session',
        '1998 General Session',
        '1997 2nd Special Session',
        '1997 1st Special Session',
        '1997 General Session',
        '1990-1996',
    ],
}


def session_list():
    sessions = url_xpath(
            'http://le.utah.gov/Documents/bills.htm',
            '//p/a[contains(@href, "session")]/text()'
            )
    return [ re.sub(r'\s+', ' ', session.strip()) for session in sessions ]


def extract_text(doc, data):
    if doc['mimetype'] == 'application/pdf':
        return text_after_line_numbers(pdfdata_to_text(data))
