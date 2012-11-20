import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=300)

# most info taken from http://www.kslib.info/constitution/art2.html
# also ballotpedia.org
metadata = dict(
    name='Kansas',
    abbreviation='ks',
    legislature_name='Kansas State Legislature',
    capitol_timezone='America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '2011-2012': {
            'start_date': datetime.date(2011, 1, 12),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2011_12',
        },
    },
    feature_flags=['influenceexplorer'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    url = url_xpath('http://www.kslegislature.org/li',
                     '//a[contains(text(), "Senate Bills")]/@href')[0]
    slug = url.split('/')[2]
    return [slug]


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
