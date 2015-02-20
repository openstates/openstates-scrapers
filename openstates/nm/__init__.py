import scrapelib
import lxml.html

UAS = scrapelib._user_agent = "Mozilla/5.0 (compatible; %s)" % (
    scrapelib._user_agent)

scrapelib._user_agent = UAS
scrapelib._default_scraper.user_agent = UAS

from .bills import NMBillScraper
from .legislators import NMLegislatorScraper



metadata = {
    'abbreviation': 'nm',
    'name': 'New Mexico',
    'legislature_name': 'New Mexico Legislature',
    'legislature_url': 'http://www.nmlegis.gov/',
    'capitol_timezone': 'America/Denver',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012',
         'sessions': ['2011', '2011S', '2012'],
         'start_year': 2011, 'end_year': 2012,
        },
        {'name': '2013-2014',
         'sessions': ['2013', '2014'],
         'start_year': 2013, 'end_year': 2014,
        },
        {'name': '2015-2016',
         'sessions': ['2015'],
         'start_year': 2015, 'end_year': 2016,
        }
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'slug': '11%20Regular',
                 '_scraped_name': '2011 Regular',
                },
        '2011S': {'display_name': '2011 Special Session',
                  'slug': '11%20Special',
                  '_scraped_name': '2011 1st Special',
                 },
        '2012': {'display_name': '2012 Regular Session',
                 'slug': '12%20Regular',
                 '_scraped_name': '2012 Regular',
                },
        '2013': {'display_name': '2013 Regular Session',
                 'slug': '13%20Regular',
                 '_scraped_name': '2013 Regular',
                },
        '2014': {'display_name': '2014 Regular Session',
                 'slug': '14%20Regular',
                 '_scraped_name': '2014 Regular',
                },
        '2015': {'display_name': '2015 Regular Session',
                 'slug': '15%20Regular',
                 '_scraped_name': '2015 Regular',
                },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2010 2nd Special', '2010 Regular',
                                  '2009 1st Special', '2009 Regular',
                                  '2008 2nd Special', '2008 Regular',
                                  '2007 1st Special', '2007 Regular',
                                  '2006 Regular', '2005 1st Special',
                                  '2005 Regular', '2004 Regular',
                                  '2003 1st Special', '2003 Regular',
                                  '2002 Extraordinary', '2002 Regular',
                                  '2001 2nd Special', '2001 1st Special',
                                  '2001 Regular', '2000 2nd Special',
                                  '2000 Regular', '1999 1st Special',
                                  '1999 Regular', '1998 1st Special',
                                  '1998 Regular', '1997 Regular',
                                  '1996 1st Special', '1996 Regular']
}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.nmlegis.gov/lcs/keyword.aspx',
        "//select[@name='ctl00$mainCopy$ddlSessions']/option/text()" )

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//body')[0].text_content().split(
        u'\r\n\xa0\r\n\xa0\r\n\xa0')[-1]
