from billy.utils.fulltext import text_after_line_numbers
import lxml.html
from .bills import FLBillScraper
from .legislators import FLLegislatorScraper
from .committees import FLCommitteeScraper
from .events import FLEventScraper

metadata = dict(
    name='Florida',
    abbreviation='fl',
    capitol_timezone='America/New_York',
    legislature_name='Florida Legislature',
    legislature_url='http://www.leg.state.fl.us/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011', '2012', '2012B'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013', '2014', '2014A'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015'],
         'start_year': 2015, 'end_year': 2016}
    ],
    session_details={
        '2011': {'display_name': '2011 Regular Session',
                 '_scraped_name': '2011',
                },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012',
                },
        '2012B': {'display_name': '2012 Extraordinary Apportionment Session',
                 '_scraped_name': '2012B',
                },
        '2013': {'display_name': '2013 Regular Session',
                 '_scraped_name': '2013',
                },
        '2014': {'display_name': '2014 Regular Session',
                 '_scraped_name': '2014',
                },
        '2014A': {'display_name': '2014 Special Session A',
                 '_scraped_name': '2014A',
                },
        '2015': {'display_name': '2015 Regular Session',
                 '_scraped_name': '2015',
                },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=[
        '2010O', '2010A', '2012O', '2010',
        '2014O',  # 2014 Organizational session; nothing important here.
        ],
)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://flsenate.gov', '//option/text()')


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    pre = doc.xpath('//pre')
    if pre:
        text = pre[0].text_content().encode('ascii', 'replace')
        return text_after_line_numbers(text)
    else:
        return '\n'.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
