from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import VTBillScraper
from .legislators import VTLegislatorScraper
from .committees import VTCommitteeScraper
from .events import VTEventScraper

metadata = dict(
    name='Vermont',
    abbreviation='vt',
    capitol_timezone='America/New_York',
    legislature_name='Vermont General Assembly',
    legislature_url='http://legislature.vermont.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator', 'term': 2},
        'lower': {'name': 'House', 'title': 'Representative', 'term': 2},
    },
    terms=[{'name': '2009-2010',
            'start_year': 2009,
            'end_year': 2010,
            'sessions': ['2009-2010']},
           {'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011-2012']},
           {'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013-2014']},
           {'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015-2016']},
           ],
    session_details={'2009-2010': {'type': 'primary',
                                   'display_name': '2009-2010 Regular Session',
                                   '_scraped_name': '2009-2010 Session',
                                  },
                     '2011-2012': {'type': 'primary',
                                   'display_name': '2011-2012 Regular Session',
                                   '_scraped_name': '2011-2012 Session',
                                  },
                     '2013-2014': {'type': 'primary',
                                   'display_name': '2013-2014 Regular Session',
                                   '_scraped_name': '2013-2014 Session',
                                  },
                     '2015-2016': {'type': 'primary',
                                   'display_name': '2015-2016 Regular Session',
                                   '_scraped_name': '2015-2016 Session',
                                  },
                     },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions= ['2009 Special Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath(
            'http://legislature.vermont.gov/bill/search/2016',
            '//fieldset/div[@id="selected_session"]/div/select/option/text()')

def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
