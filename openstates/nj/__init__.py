import datetime
import lxml.html
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import text_after_line_numbers
from .bills import NJBillScraper
from .legislators import NJLegislatorScraper
from .committees import NJCommitteeScraper
from .events import NJEventScraper

# don't retry- if a file isn't on FTP just let it go
settings = dict(SCRAPELIB_RETRY_ATTEMPTS=0)

metadata = {
    'name': 'New Jersey',
    'abbreviation': 'nj',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'New Jersey Legislature',
    'legislature_url': 'http://www.njleg.state.nj.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assembly Member'},
    },
    'terms': [
        #{
        #    'name': '2000-2001',
        #    'start_year': 2000,
        #    'end_year': 2001,
        #    'sessions': ['209'],
        #},
        #{
        #    'name': '2002-2003',
        #    'start_year': 2002,
        #    'end_year': 2003,
        #    'sessions': ['210'],
        #},
        #{
        #    'name': '2004-2005',
        #    'start_year': 2004,
        #    'end_year': 2005,
        #    'sessions': ['211'],
        #},
        #{
        #    'name': '2006-2007',
        #    'start_year': 2006,
        #    'end_year': 2007,
        #    'sessions': ['212'],
        #},
        {
            'name': '2008-2009',
            'start_year': 2008,
            'end_year': 2009,
            'sessions': ['213'],
        },
        {
            'name': '2010-2011',
            'start_year': 2010,
            'end_year': 2011,
            'sessions': ['214'],    
        },
        {
            'name': '2012-2013',
            'start_year': 2012,
            'end_year': 2013,
            'sessions': ['215'],
        },
        {
            'name': '2014-2015',
            'start_year': 2014,
            'end_year': 2015,
            'sessions': ['216'],
        },
        {
            'name': '2016-2017',
            'start_year': 2016,
            'end_year': 2017,
            'sessions': ['217'],
        },
    ],
    'session_details': {
        '213': {
            'start_date': datetime.date(2008, 1, 12),
            'display_name': '2008-2009 Regular Session',
            '_scraped_name': '2008-2009',
        },
        '214': {
            'start_date': datetime.date(2010, 1, 12),
            'display_name': '2010-2011 Regular Session',
            '_scraped_name': '2010-2011',
        },
        '215': {
            'start_date': datetime.date(2012, 1, 10),
            'display_name': '2012-2013 Regular Session',
            '_scraped_name': '2012-2013',
        },
        '216': {
            'start_date': datetime.date(2014, 1, 15),
            'display_name': '2014-2015 Regular Session',
            '_scraped_name': '2014-2015',
        },
        '217': {
            'start_date': datetime.date(2016, 1, 12),
            'display_name': '2016-2017 Regular Session',
            '_scraped_name': '2016-2017',
        },
    },
    'feature_flags': ['subjects', 'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2006-2007',
        '2004-2005',
        '2002-2003',
        '2000-2001',
        '1998-1999',
        '1996-1997',
    ],
}


def session_list():
    return url_xpath('http://www.njleg.state.nj.us/',
                     '//select[@name="DBNAME"]/option/text()')


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//div[@class="Section3"]')[0].text_content()
    return text
