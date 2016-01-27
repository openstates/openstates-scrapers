from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import HIBillScraper
from .legislators import HILegislatorScraper
from .events import HIEventScraper

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    capitol_timezone='Pacific/Honolulu',
    legislature_name='Hawaii State Legislature',
    legislature_url='http://www.capitol.hawaii.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        {
            'name': '2011-2012',
            'sessions': [
                '2011 Regular Session',
            ],
            'start_year' : 2011,
            'end_year'   : 2012
        },
        {
            'name': '2013-2014',
            'sessions': [
                '2013 Regular Session',
                '2014 Regular Session',
            ],
            'start_year' : 2013,
            'end_year'   : 2014
        },
        {
            'name': '2015-2016',
            'sessions': [
                '2015 Regular Session',
                '2016 Regular Session',
            ],
            'start_year' : 2015,
            'end_year'   : 2016
        },
     ],
    session_details={
        '2016 Regular Session' : {
            'display_name'  : '2016 Regular Session',
            '_scraped_name' : '2016'
        },
        '2015 Regular Session' : {
            'display_name'  : '2015 Regular Session',
            '_scraped_name' : '2015'
        },
        '2014 Regular Session' : {
            'display_name'  : '2014 Regular Session',
            '_scraped_name' : '2014'
        },
        '2013 Regular Session' : {
            'display_name'  : '2013 Regular Session',
            '_scraped_name' : '2013'
        },
        '2011 Regular Session' : {
            'display_name'  : '2011-2012 Regular Session',
            # was 2011, now 2012 to make scraper keep working for 2011-2012
            '_scraped_name' : '2012'
        },
    },
    feature_flags=['subjects', 'events', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Chamber Floor",
         "url": 'http://static.openstates.org/capmaps/hi/floorchamber.pdf'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/hi/floor2.pdf'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/hi/floor3.pdf'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/hi/floor4.pdf'
        },
        {"name": "Floor 5",
         "url": 'http://static.openstates.org/capmaps/hi/floor5.pdf'
        },
    ],
    _ignored_scraped_sessions = [
        # ignore odd years after they're over..
        '2011',
        '2010', '2009', '2008', '2007', '2006',
        '2005', '2004', '2003', '2002', '2001',
        '2000', '1999'
    ]
)

def session_list():
    # doesn't include current session, we need to change it
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://www.capitol.hawaii.gov/archives/main.aspx',
            "//div[@class='roundedrect gradientgray shadow']/a/text()"
        )
    sessions.remove("Archives Main")
    return sessions

def extract_text(doc, data):
    if doc['mimetype'] == 'application/pdf':
        return text_after_line_numbers(pdfdata_to_text(data))
