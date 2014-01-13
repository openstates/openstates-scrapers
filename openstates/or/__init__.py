import re
import lxml.html
from .bills import ORBillScraper
from .legislators import ORLegislatorScraper

metadata = dict(
    name='Oregon',
    abbreviation='or',
    capitol_timezone='America/Los_Angeles',
    legislature_name='Oregon Legislative Assembly',
    legislature_url='http://www.leg.state.or.us/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session',
                      '2012 Regular Session',
                      '2012 Special Session' ],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013 Regular Session',
                      '2014 Regular Session'],
         'start_year': 2013, 'end_year': 2014},
    ],
    session_details={
        '2011 Regular Session': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session',
            'slug': '11reg',
        },
        '2012 Regular Session': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session',
            'slug': '12reg',
        },
        '2012 Special Session' : {
            'display_name': '2012 Speical Session',
            '_scraped_name': '2012 Special Session',
            'slug': '12ss1',
        },
        '2013 Regular Session': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Regular Session',
            'slug': '13reg',
        },
        '2014 Regular Session': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Regular Session',
            'slug': '14reg',
        },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['Today',
                               '2013 1st Special Session', '2013 Interim',
                               '2012 1st Special Session', '2011 Interim',
                               '2010 Special Session', '2009 Interim',
                               '2009 Regular Session', '2008 Special Session',
                               '2007 Interim', '2007 Regular Session']
)

def session_list():
    from billy.scrape.utils import url_xpath
    return [x.strip() for x in
            url_xpath('https://olis.leg.state.or.us/liz/sessions/',
                      '//a[contains(@href, "/liz/")]/text()')]

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    lines = doc.xpath('//pre/text()')[0].splitlines()
    text = ' '.join(line for line in lines
                    if not re.findall('Page \d+$', line))
    return text
