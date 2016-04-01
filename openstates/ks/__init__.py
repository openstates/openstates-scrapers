import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import KSBillScraper
from .legislators import KSLegislatorScraper
from .committees import KSCommitteeScraper

settings = dict(SCRAPELIB_TIMEOUT=300)

# most info taken from http://www.kslib.info/constitution/art2.html
# also ballotpedia.org
metadata = dict(
    name='Kansas',
    abbreviation='ks',
    legislature_name='Kansas State Legislature',
    legislature_url='http://www.kslegislature.org/',
    capitol_timezone='America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012,},
        {'name': '2013-2014',
         'sessions': ['2013-2014'],
         'start_year': 2013, 'end_year': 2014,},
        {'name': '2015-2016',
         'sessions': ['2015-2016'],
         'start_year': 2015, 'end_year': 2016,},
    ],
    session_details={
        '2011-2012': {
            'start_date': datetime.date(2011, 1, 12),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2011_12',
        },
        '2013-2014': {
            'start_date': datetime.date(2013, 1, 14),
            'display_name': '2013-2014 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2013_14',
        },
        '2015-2016': {
            'start_date': datetime.date(2013, 1, 14),
            'display_name': '2015-2016 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2015_16',
        },
    },
    feature_flags=['influenceexplorer'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    url = url_xpath('http://www.kslegislature.org/li',
        '//div[@id="nav"]//a[contains(text(), "Senate Bills")]/@href')[0]
    slug = url.split('/')[2]
    return [slug]


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
