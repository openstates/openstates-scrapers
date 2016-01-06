import datetime
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import RIBillScraper
from .legislators import RILegislatorScraper
from .committees import RICommitteeScraper
from .events import RIEventScraper
from .votes import RIVoteScraper

metadata = {
    'name': 'Rhode Island',
    'abbreviation': 'ri',
    'legislature_name': 'Rhode Island General Assembly',
    'legislature_url': 'http://www.rilin.state.ri.us/',
    'capitol_timezone': 'America/New_York',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2012',
            'start_year': 2012,
            'end_year': 2012,
            'sessions': ['2012'],
        },
        {
            'name': '2013',
            'start_year': 2013,
            'end_year': 2013,
            'sessions': ['2013'],
        },

        {
            'name': '2014',
            'start_year': 2014,
            'end_year': 2014,
            'sessions': ['2014'],
        },
        {
            'name': '2015',
            'start_year': 2015,
            'end_year': 2015,
            'sessions': ['2015'],
        },
        {
            'name': '2016',
            'start_year': 2016,
            'end_year': 2017,
            'sessions': ['2016'],
        },
    ],
    'session_details': {
        '2012': {
            'type': 'primary',
            'start_date': datetime.date(2012, 1, 3),
            'end_date': datetime.date(2012, 6, 13),
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012',
        },
        '2013': {
            'type': 'primary',
            'start_date': datetime.date(2013, 1, 1),
            'end_date': datetime.date(2013, 7, 3),
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        },
        '2014': {
            'type': 'primary',
            'start_date': datetime.date(2014, 1, 7),
            'end_date': datetime.date(2014, 6, 21),
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014',
        },
        '2015': {
            'type': 'primary',
            'start_date': datetime.date(2015, 1, 6),
            'end_date': datetime.date(2015, 6, 25),
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015',
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016, 1, 5),
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016',
        },
    },
    'feature_flags': ['subjects', 'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2015',
        '2014',
        '2013',
        '2012',
        '2011',
        '2010',
        '2009',
        '2008',
        '2007'
    ],
    '_partial_vote_bill_id': True,
}


def session_list():
    return url_xpath(
        'http://status.rilin.state.ri.us/bill_history.aspx?mode=previous',
        '//select[@name="ctl00$rilinContent$cbYear"]/option/text()')


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
