import datetime
import lxml.html
import logging
from billy.utils.fulltext import text_after_line_numbers
from billy.scrape.utils import url_xpath
from .bills import VABillScraper
from .legislators import VALegislatorScraper

settings = {
    'SCRAPELIB_RPM': 40
}

metadata = {
    'name': 'Virginia',
    'abbreviation': 'va',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Virginia General Assembly',
    'legislature_url': 'http://virginiageneralassembly.gov/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Delegate'},
    },
    'terms': [
        {
            'name': '2009-2011',
            'sessions': ['2010', '2011', '2011specialI'],
            'start_year': 2010,
            'end_year': 2011,
        },
        {
            'name': '2012-2013',
            'sessions': ['2012', '2012specialI', '2013', '2013specialI'],
            'start_year': 2012,
            'end_year': 2013,
        },
        {
            'name': '2014-2015',
            'sessions': ['2014', '2014specialI', '2015', '2015specialI'],
            'start_year': 2014,
            'end_year': 2015,
        },
        {
            'name': '2016-2017',
            'sessions': ['2016','2017'],
            'start_year': 2016,
            'end_year': 2017,
        },
    ],
    'session_details': {
        '2010': {
            'start_date': datetime.date(2010, 1, 13),
            'site_id': '101',
            'display_name': '2010 Regular Session',
            '_scraped_name': '2010 Session',
        },
        '2011': {
            'start_date': datetime.date(2011, 1, 12),
            'site_id': '111',
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Session',
        },
        '2011specialI': {
            'site_id': '112',
            'display_name': '2011, 1st Special Session',
            '_scraped_name': '2011 Special Session I',
        },
        '2012': {
            'start_date': datetime.date(2012, 1, 11),
            'site_id': '121',
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Session',
        },
        '2012specialI': {
            'start_date': datetime.date(2012, 3, 11),
            'site_id': '122',
            'display_name': '2012, 1st Special Session',
            '_scraped_name': '2012 Special Session I',
        },
        '2013': {
            'start_date': datetime.date(2013, 1, 9),
            'site_id': '131',
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Session',
        },
        '2013specialI': {
            'site_id': '132',
            'display_name': '2013, 1st Special Session',
            '_scraped_name': '2013 Special Session I',
        },
        '2014': {
            'start_date': datetime.date(2014, 1, 9),
            'site_id': '141',
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Session',
        },
        '2014specialI': {
            'site_id': '142',
            'display_name': '2014, 1st Special Session',
            '_scraped_name': '2014 Special Session I',
        },
        '2015': {
            'start_date': datetime.date(2015, 1, 14),
            'end_date': datetime.date(2015, 2, 27),
            'site_id': '151',
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 Session',
        },
        '2015specialI': {
            'start_date': datetime.date(2015, 8, 17),
            'end_date': datetime.date(2015, 8, 17),
            'site_id': '152',
            'display_name': '2015, 1st Special Session',
            '_scraped_name': '2015 Special Session I',
        },
        '2016': {
            'start_date': datetime.date(2016, 1, 13),
            'end_date': datetime.date(2016, 3, 12),
            'site_id': '161',
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 Session',
        },
        '2017': {
            'start_date': datetime.date(2017, 1, 11),
            'end_date': datetime.date(2017, 2, 9),
            'site_id': '171',
            'display_name': '2017 Regular Session',
            '_scraped_name': '2017 Session',
        },        
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2015 Special Session I',
        '2015 Session',
        '2014 Special Session I',
        '2014 Session',
        '2013 Special Session I',
        '2013 Session',
        '2012 Special Session I',
        '2012 Session',
        '2011 Special Session I',
        '2011 Session',
        '2010 Session',
        '2009 Session',
        '2009 Special Session I',
        '2008 Session',
        '2008 Special Session I',
        '2008 Special Session II',
        '2007 Session',
        '2006 Session',
        '2006 Special Session I',
        '2005 Session',
        '2004 Session',
        '2004 Special Session I',
        '2004 Special Session II',
        '2003 Session',
        '2002 Session',
        '2001 Session',
        '2001 Special Session I',
        '2000 Session',
        '1999 Session',
        '1998 Session',
        '1998 Special Session I',
        '1997 Session',
        '1996 Session',
        '1995 Session',
        '1994 Session',
        '1994 Special Session I',
        '1994 Special Session II',
    ]
}


def session_list():
    sessions = url_xpath( 'http://lis.virginia.gov/',
        "//div[@id='sLink']//select/option/text()")
    sessions = [s.strip() for s in sessions if 'Session' in s]

    return sessions


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content()
        for x in doc.xpath('//div[@id="mainC"]/p'))
    return text
