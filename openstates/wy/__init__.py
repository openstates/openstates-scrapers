import re
import datetime
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import pdfdata_to_text
from .bills import WYBillScraper
from .legislators import WYLegislatorScraper
from .committees import WYCommitteeScraper
from .events import WYEventScraper

metadata = {
    'name': 'Wyoming',
    'abbreviation': 'wy',
    'legislature_name': 'Wyoming State Legislature',
    'legislature_url': 'http://legisweb.state.wy.us/',
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
            'sessions': ['2011','2012'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2014'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015', '2016'],
        },
    ],
    'session_details': {
        '2011': {
            'type': 'primary',
            'display_name': '2011 General Session',
            '_scraped_name': '2011 General Session'
        },
        '2012': {
            'type': 'special',
            'display_name': '2012 Budget Session',
            '_scraped_name': '2012 Budget Session'
        },
        '2013': {
            'type': 'primary',
            'display_name': '2013 General Session',
            '_scraped_name': '2013 General Session'
        },
        '2014': {
            'type': 'primary',
            'display_name': '2014 General Session',
            '_scraped_name': '2014 General Session'
        },
        '2015': {
            'type': 'primary',
            'display_name': '2015 General Session',
            '_scraped_name': '2015 General Session'
        },
        '2016': {
            'type': 'primary',
            'display_name': '2016 General Session',
            '_scraped_name': '2016 General Session',
        },
    },
    'feature_flags': ['influenceexplorer', 'events'],
    # The reason the Budget sessions are in ignore is because the budget
    # session is just for the budget bill, which is HB 1
    # (http://openstates.org/wy/bills/2014/HB1/)
    # So - we avoid the new session, because we'd dupe all bills.
    '_ignored_scraped_sessions': [
        '2016 Budget Session',
        '2014 Budget Session',
        '2010 Budget Session',
        '2009 General Session',
        '2008 Budget Session',
        '2007 General Session',
        '2006 Budget Session',
        '2005 General Session',
        '2004 Budget Session',
        '2003 General Session',
        '2002 Budget Session',
        '2001 General Session',
    ],
}


def session_list():
    sessions = url_xpath('http://legisweb.state.wy.us/LSOWeb/SessionArchives'
        '.aspx', '//div[@id="divLegContent"]/a/p/text()')

    return sessions


def extract_text(doc, data):
    return ' '.join(line for line in pdfdata_to_text(data).splitlines()
                    if re.findall('[a-z]', line))
