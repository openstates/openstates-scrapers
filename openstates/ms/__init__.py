import datetime
import lxml.html
from billy.scrape.utils import url_xpath
from .bills import MSBillScraper
from .legislators import MSLegislatorScraper
from .committees import MSCommitteeScraper

metadata = {
    'name': 'Mississippi',
    'abbreviation': 'ms',
    'legislature_name': 'Mississippi Legislature',
    'legislature_url': 'http://www.legislature.ms.gov/',
    'capitol_timezone': 'America/Chicago',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2008-2011',
            'start_year': 2008,
            'end_year': 2011,
            'sessions': [
                '2008',
                '2009', '20091E', '20092E', '20093E',
                '2010', '20101E', '20102E',
                '2011', '20111E',
            ],
        },
        {
            'name': '2012-2015',
            'start_year': 2012, 'end_year': 2015,
            'sessions': [
                '2012',
                '2013', '20131E', '20132E',
                '2014', '20141E', '20142E',
                '2015',
            ],
        },
        {
            'name': '2016-2019',
            'start_year': 2016, 'end_year': 2019,
            'sessions': [
                '2016', '20161E'
            ],
        },
    ],
    'session_details': {
        '2008': {
            'display_name': '2008 Regular Session',
            '_scraped_name': '2008 Regular Session',
        },
        '2009': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009 Regular Session',
        },
        '20091E': {
            'display_name': '2009, 1st Extraordinary Session',
            '_scraped_name': '2009 First Extraordinary Session',
        },
        '20092E': {
            'display_name': '2009, 2nd Extraordinary Session',
            '_scraped_name': '2009 Second Extraordinary Session',
        },
        '20093E': {
            'display_name': '2009, 3rd Extraordinary Session',
            '_scraped_name': '2009 Third Extraordinary Session',
        },
        '20101E': {
            'display_name': '2010, 1st Extraordinary Session',
            '_scraped_name': '2010 First Extraordinary Session',
        },
        '20102E': {
            'display_name': '2010, 2nd Extraordinary Session',
            '_scraped_name': '2010 Second Extraordinary Session',
        },
        '2010': {
            'display_name': '2010 Regular Session',
            '_scraped_name': '2010 Regular Session',
        },
        '2011': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session',
        },
        '20111E': {
            'display_name': '2011, 1st Extraordinary Session',
            '_scraped_name': '2011 First Extraordinary Session',
        },
        '2012': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session',
        },
        '2013': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Regular Session',
        },
        '20131E': {
            'display_name': '2013 First Extraordinary Session',
            '_scraped_name': '2013 First Extraordinary Session'
        },
        '20132E': {
            'display_name': '2013 Second Extraordinary Session',
            '_scraped_name': '2013 Second Extraordinary Session'
        },
        '2014': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Regular Session'
        },
        '20141E': {
            'display_name': '2014 First Extraordinary Session',
            '_scraped_name': '2014 First Extraordinary Session'
        },
        '20142E': {
            'display_name': '2014 Second Extraordinary Session',
            '_scraped_name': '2014 Second Extraordinary Session'
        },
        '2015': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 Regular Session'
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016, 1, 5),
            'end_date': datetime.date(2016, 5, 8),
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 Regular Session',
        },
        '20161E': {
            'display_name': '2016 First Extraordinary Session',
            '_scraped_name': '2016 First Extraordinary Session'
        },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2008 First Extraordinary Session',
        '2007 Regular Session',
        '2007 First Extraordinary Session',
        '2006 Regular Session',
        '2006 First Extraordinary Session',
        '2006 Second Extraordinary Session',
        '2005 Regular Session',
        '2005 First Extraordinary Session',
        '2005 Second Extraordinary Session',
        '2005 Third Extraordinary Session',
        '2005 Fourth Extraordinary Session',
        '2005 Fifth Extraordinary Session',
        '2004 Regular Session',
        '2004 First Extraordinary Session',
        '2004 Second Extraordinary Session',
        '2004 Third Extraordinary Session',
        '2003 Regular Session',
        '2002 Regular Session',
        '2002 First Extraordinary Session',
        '2002 Second Extraordinary Session',
        '2002 Third Extraordinary Session',
        '2001 Regular Session',
        '2001 First Extraordinary Session',
        '2001 Second Extraordinary Session',
        '2000 Regular Session',
        '2000 First Extraordinary Session',
        '2000 Second Extraordinary Session',
        '2000 Third Extraordinary Session',
        '1999 Regular Session',
        '1998 Regular Session',
        '1997 Regular Session',
    ],
}


def session_list():
    return url_xpath('http://billstatus.ls.state.ms.us/sessions.htm',
        '//a/text()')


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(p.text_content() for p in
        doc.xpath('//h2/following-sibling::p'))
    return text
