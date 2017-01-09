import lxml.html
from .bills import NHBillScraper
from .legislators import NHLegislatorScraper
from .committees import NHCommitteeScraper
from . import utils

metadata = {
    'abbreviation': 'nh',
    'name': 'New Hampshire',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'New Hampshire General Court',
    'legislature_url': 'http://www.gencourt.state.nh.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['2013', '2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['2015', '2016'],
         'start_year': 2015, 'end_year': 2016}
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2011%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2011 Session',
                },
        '2012': {'display_name': '2012 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2012%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2012 Session',
                },
        '2013': {'display_name': '2013 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2013%20Session%20Bill%20Status%20Tables.zip',
                 # Their dump filename changed, probably just a hiccup.
                 '_scraped_name': '2013',
                 # '_scraped_name': '2013 Session',
                },
        '2014': {'display_name': '2014 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2014%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2014 Session',
                },
        '2015': {'display_name': '2015 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2015%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2015 Session',
                },
        '2016': {'display_name': '2016 Regular Session',
                 'zip_url': 'http://gencourt.state.nh.us/downloads/2016%20Session%20Bill%20Status%20Tables.zip',
                 '_scraped_name': '2016 Session',
                },                
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2013 Session'],
}

def session_list():
    from billy.scrape.utils import url_xpath
    zips = url_xpath('http://gencourt.state.nh.us/downloads/',
                     '//a[contains(@href, "Bill%20Status%20Tables")]/text()')
    return [zip.replace(' Bill Status Tables.zip', '') for zip in zips]

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//html')[0].text_content()
