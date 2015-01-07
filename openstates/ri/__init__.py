import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import RIBillScraper
from .legislators import RILegislatorScraper
from .committees import RICommitteeScraper
from .events import RIEventScraper
from .votes import RIVoteScraper

metadata = dict(
    _partial_vote_bill_id=True,

    name='Rhode Island',
    abbreviation='ri',
    capitol_timezone='America/New_York',
    legislature_name='Rhode Island General Assembly',
    legislature_url='http://www.rilin.state.ri.us/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2012',
         'start_year': 2012,
         'start_date': datetime.date(2012, 1, 4),
         'end_year': 2012,
         'sessions': ['2012']},
        {'name': '2013',
         'start_year': 2013,
         'end_year': 2014,
         'sessions': ['2013']},
        {'name': '2014',
         'start_year': 2014,
         'end_year': 2015,
         'sessions': ['2014']},
        {'name': '2015',
         'start_year': 2015,
         'end_year': 2016,
         'sessions': ['2015']},
    ],
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    session_details={

        '2012': {'start_date': datetime.date(2012, 1, 4),
                 '_scraped_name': '2012',
                 'type': 'primary',
                 'display_name': '2012 Regular Session'},

        '2013': {'type': 'primary',
                 '_scraped_name': '2013',
                 'display_name': '2013 Regular Session'},

        '2014': {'type': 'primary',
                 '_scraped_name': '2014',
                 'display_name': '2014 Regular Session'},

        '2015': {'type': 'primary',
                 '_scraped_name': '2015',
                 'display_name': '2015 Regular Session'},
    },
    _ignored_scraped_sessions=['2011', '2010', '2009', '2008', '2007']
)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://status.rilin.state.ri.us/bill_history.aspx?mode=previous',
                     "//select[@name='ctl00$rilinContent$cbYear']/option/text()")


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
