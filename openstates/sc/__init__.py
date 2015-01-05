import lxml.html
import datetime
from .bills import SCBillScraper
from .legislators import SCLegislatorScraper
from .events import SCEventScraper

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='South Carolina',
    abbreviation='sc',
    capitol_timezone='America/New_York',
    legislature_name='South Carolina Legislature',
    legislature_url='http://www.scstatehouse.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '119',
         'sessions': ['119'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013-2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015-2016'],
         'start_year': 2015, 'end_year': 2016},
        ],
    session_details={
        '119': {
            'start_date': datetime.date(2010, 11, 17), 'type': 'primary',
            '_scraped_name': '119 - (2011-2012)',
            'display_name': '2011-2012 Regular Session'
        },
        '2013-2014': {
            'start_date': datetime.date(2013, 1, 8), 'type': 'primary',
            '_scraped_name': '120 - (2013-2014)',
            'display_name': '2013-2014 Regular Session',
            '_code': '120',
        },
        '2015-2016': {
            'start_date': datetime.date(2015, 1, 13), 'type': 'primary',
            '_scraped_name': '121 - (2015-2016)',
            'display_name': '2015-2016 Regular Session',
            '_code': '121',
        },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['118 - (2009-2010)', '117 - (2007-2008)',
                               '116 - (2005-2006)', '115 - (2003-2004)',
                               '114 - (2001-2002)', '113 - (1999-2000)',
                               '112 - (1997-1998)', '111 - (1995-1996)',
                               '110 - (1993-1994)', '109 - (1991-1992)',
                               '108 - (1989-1990)', '107 - (1987-1988)',
                               '106 - (1985-1986)', '105 - (1983-1984)',
                               '104 - (1981-1982)', '103 - (1979-1980)',
                               '102 - (1977-1978)', '101 - (1975-1976)']

)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.scstatehouse.gov/billsearch.php',
        "//select[@id='session']/option/text()" )

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    # trim first and last part
    text = ' '.join(p.text_content() for p in doc.xpath('//p')[1:-1])
    return text
