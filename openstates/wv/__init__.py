import lxml.html

from .bills import WVBillScraper
from .legislators import WVLegislatorScraper
from .committees import WVCommitteeScraper


metadata = {
    'abbreviation': 'wv',
    'capitol_timezone': 'America/New_York',
    'name': 'West Virginia',
    'legislature_name': 'West Virginia Legislature',
    'legislature_url': 'http://www.legis.state.wv.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Delegate'},
    },
    'terms': [
        {'name': '2011-2012',
         'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011', '2012'],
         },
        {'name': '2013-2014',
         'start_year': 2013, 'end_year': 2014,
         'sessions': ['2013', '2014'],
         },
        {'name': '2015-2016',
         'start_year': 2015, 'end_year': 2016,
         'sessions': ['2015', '2016', '20161S'],
         }
        ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2011'                
                 },
        '2012': {'display_name': '2012 Regular Session',
                'type': 'primary',
                 '_scraped_name': '2012'
                 },
        '2013': {'display_name': '2013 Regular Session',
                'type': 'primary',
                 '_scraped_name': '2013'
                 },
        '2014': {'display_name': '2014 Regular Session',
                'type': 'primary',
                 '_scraped_name': '2014'
                 },
        '2015': {'display_name': '2015 Regular Session',
                'type': 'primary',
                 '_scraped_name': '2015'
                 },
        '2016': {'display_name': '2016 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2016'
                 },
        '20161S': {'display_name': '2016 First Special Session',
                 'type':'special',
                 '_scraped_name': '2016',
                 '_special_name': '1X'
                 },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2010', '2009', '2008', '2007', '2006',
        '2005', '2004', '2003', '2002', '2001',
        '2000', '1999', '1998', '1997', '1996',
        '1995', '1994', '1993',
        ]
}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.wv.us/Bill_Status/Bill_Status.cfm',
                     '//select[@name="year"]/option/text()')


def extract_text(doc, data):
    if (doc.get('mimetype') == 'text/html' or 'bills_text.cfm' in doc['url']):
        doc = lxml.html.fromstring(data)
        return '\n'.join(p.text_content() for p in
                         doc.xpath('//div[@id="bhistcontent"]/p'))
