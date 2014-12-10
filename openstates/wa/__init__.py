import lxml.html
from billy.utils.fulltext import text_after_line_numbers
from .bills import WABillScraper
from .legislators import WALegislatorScraper
from .committees import WACommitteeScraper
from .events import WAEventScraper

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Washington',
    abbreviation='wa',
    capitol_timezone='America/Los_Angeles',
    legislature_name='Washington State Legislature',
    legislature_url='http://www.leg.wa.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'start_year': 2009, 'end_year': 2010,
         'sessions': ['2009-2010']},
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011-2012']},
        {'name': '2013-2014', 'start_year': 2013, 'end_year': 2014,
         'sessions': ['2013-2014']},
        {'name': '2015-2016', 'start_year': 2015, 'end_year': 2016,
         'sessions': ['2015-2016']},
        ],
    session_details = {
        '2009-2010': {'display_name': '2009-2010 Regular Session',
                      '_scraped_name': '2009-10',
                     },
        '2011-2012': {'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-12',
                     },
        '2013-2014': {'display_name': '2013-2014 Regular Session',
                      '_scraped_name': '2013-14',
                     },
        '2015-2016': {'display_name': '2015-2016 Regular Session',
                      '_scraped_name': '2015-16',
                     },
    },
    feature_flags = ['events', 'subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/wa/f1.gif'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/wa/f2.gif'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/wa/f3.gif'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/wa/f4.gif'
        },
    ],
    _ignored_scraped_sessions=['2007-08'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://apps.leg.wa.gov/billinfo/',
     '//td[starts-with(@id, "ctl00_ContentPlaceHolder1_TabControl1")]/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//body/p'))
    return text
