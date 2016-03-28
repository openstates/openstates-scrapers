from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import MTBillScraper
from .legislators import MTLegislatorScraper
from .committees import MTCommitteeScraper

metadata = {
    'name': 'Montana',
    'abbreviation': 'mt',
    'legislature_name': 'Montana Legislature',
    'legislature_url': 'http://leg.mt.gov/',
    'capitol_timezone': 'America/Denver',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012',
         'sessions': ['2011'],
         'session_number': '62nd',
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013'],
         'session_number': '63rd',
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015'],
         'session_number': '64th',
         'start_year': 2015, 'end_year': 2016},
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'years': [2011, 2012],
                 '_scraped_name': '2011 Regular Session',
                },
        '2013': {'display_name': '2013 Regular Session',
                 'years': [2013, 2014],
                 '_scraped_name': '2013 Regular Session',
                },
        '2015': {'display_name': '2015 Regular Session',
                 'years': [2015],
                 '_scraped_name': '2015 Regular Session',
                },
    },
    'feature_flags': ['influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2017 Regular Session',
        '2009 Regular Session',
        '2007 Special     Session',
        '2007 Regular Session',
        '2005 Special     Session',
        '2005 Regular Session',
        '2003 Regular Session',
        '2002 Special     Session',
        '2001 Regular Session',
        '2000 Special     Session',
        '1999 Regular Session',
        '1999 Special     Session']
}


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://leg.mt.gov/css/bills/Default.asp',
        "//td[@id='cont']/ul/li/a/text()")


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
