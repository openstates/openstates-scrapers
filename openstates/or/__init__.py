import re
import lxml.html
from .bills import ORBillScraper
from .legislators import ORLegislatorScraper
from .committees import ORCommitteeScraper

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
        {'name': '2007-2008',
         'sessions': ['2007 Regular Session',
                      '2008 Special Session' ],
         'start_year': 2007, 'end_year': 2008},
        {'name': '2009-2010',
         'sessions': ['2009 Regular Session',
                      '2010 Special Session' ],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session',
                      '2012 Regular Session',
                      '2012 Special Session' ],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013 Regular Session',
                      '2013 Special Session',
                      '2014 Regular Session'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015 Regular Session',
                      '2016 Regular Session',],
         'start_year': 2015, 'end_year': 2016},
    ],
    session_details={
        '2007 Regular Session': {
            'display_name': '2007 Regular Session',
            '_scraped_name': '2007 Regular Session',
            'slug': '2007R1',
        },
        '2008 Special Session': {
            'display_name': '2008 Special Session',
            '_scraped_name': '2008 Special Session',
            'slug': '2008S1',
        },
        '2009 Regular Session': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009 Regular Session',
            'slug': '2009R1',
        },
        '2010 Special Session': {
            'display_name': '2010 Special Session',
            '_scraped_name': '2010 Special Session',
            'slug': '2010S1',
        },
        '2011 Regular Session': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session',
            'slug': '2011R1',
        },
        '2012 Regular Session': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session',
            'slug': '2012R1',
        },
        '2012 Special Session' : {
            'display_name': '2012 Speical Session',
            '_scraped_name': '2012 Special Session',
            'slug': '2012S1',
        },
        '2013 Regular Session': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Regular Session',
            'slug': '2013R1',
        },
        '2013 Special Session': {
            'display_name': '2013 Special Session',
            '_scraped_name': '2013 Special Session',
            'slug': '2013S1',
        },
        '2014 Regular Session': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Regular Session',
            'slug': '2014R1',
        },
        '2015 Regular Session': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 Regular Session',
            'slug': '2015R1',
        },
        '2016 Regular Session': {
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 Regular Session',
            'slug': '2016R1',
        },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['Today',
                               '2015-2016 Interim',
                               '2013 1st Special Session',
                               '2012 1st Special Session',
                               '2013 - 2014 Interim',
                               '2011 - 2012 Interim',
                               '2009 - 2010 Interim',
                               '2007 - 2008 Interim']
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
