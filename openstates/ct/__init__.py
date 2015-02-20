import lxml.html
from .bills import CTBillScraper
from .legislators import CTLegislatorScraper
from .events import CTEventScraper

settings = dict(SCRAPELIB_RPM = 20)

metadata = dict(
    name='Connecticut',
    capitol_timezone='America/New_York',
    abbreviation='ct',
    legislature_name='Connecticut General Assembly',
    legislature_url='http://www.cga.ct.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013', '2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015'],
         'start_year': 2015, 'end_year': 2016},
    ],
    session_details={
        '2011': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        },
        '2012': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012',
        },
        '2013': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        },
        '2014': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014',
        },
        '2015': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015',
        },
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=[
            '2005', '2006', '2007', '2008', '2009', '2010'
            ]
)

def session_list():
    import scrapelib
    text = scrapelib.urlopen('ftp://ftp.cga.ct.gov')
    sessions = [line.split()[-1] for line in text.splitlines()]
    
    for not_session_name in ('incoming', 'pub', 'CGAAudio', 'rba', 'NCSL',"apaac"):
        sessions.remove(not_session_name)
    return sessions

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(p.text_content() for p in doc.xpath('//body/p'))
    return text
