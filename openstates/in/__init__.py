import datetime
import lxml.html
from .bills import INBillScraper
from .legislators import INLegislatorScraper
from .committees import INCommitteeScraper

metadata = dict(
    name='Indiana',
    abbreviation='in',
    capitol_timezone='America/Indiana/Indianapolis',
    legislature_name='Indiana General Assembly',
    legislature_url='http://www.in.gov/legislative/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012', 'start_year': 2011,
         'end_year': 2012, 'sessions': ['2011', '2012']},
        {'name': '2013-2014', 'start_year': 2013,
         'end_year': 2014, 'sessions': ['2013']},
        ],
    session_details={
        '2011': {'start_date': datetime.date(2011, 1, 5),
                 'display_name': '2011 Regular Session',
                 '_scraped_name': '2011 Regular Session',
                },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012 Regular Session',},
        '2013': {'display_name': '2013 Regular Session',
                 '_scraped_name': '2013 Regular Session',},
        },
    feature_flags=['subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/in/floor1.gif'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/in/floor2.gif'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/in/floor3.gif'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/in/floor4.gif'
        },
    ],
    _ignored_scraped_sessions=[
        '2010 Regular Session',
        '2009 Special Session',
        '2009 Regular Session',
        '2008 Regular Session',
        '2007 Regular Session',
        '2006 Regular Session',
        '2005 Regular Session',
        '2004 Regular Session',
        '2003 Regular Session',
        '2002 Special Session',
        '2002 Regular Session',
        '2001 Regular Session',
        '2000 Regular Session',
        '1999 Regular Session',
        '1998 Regular Session',
        '1997 Regular Session']
)

def session_list():
    from billy.scrape.utils import url_xpath
    # cool URL bro
    return url_xpath('http://www.in.gov/legislative/2414.htm', '//h3/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return ' '.join(x.text_content()
                    for x in doc.xpath('//div[@align="full"]'))
