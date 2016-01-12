import datetime
import re
from billy.scrape.utils import url_xpath
from billy.utils.fulltext import worddata_to_text
from .bills import KYBillScraper
from .legislators import KYLegislatorScraper
from .committees import KYCommitteeScraper
from .events import KYEventScraper
from .votes import KYVoteScraper

metadata = {
    'name': 'Kentucky',
    'abbreviation': 'ky',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Kentucky General Assembly',
    'legislature_url': 'http://www.lrc.ky.gov/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': [
                '2011 Regular Session', '2011SS', '2012RS', '2012SS'
            ]
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': [
                '2013RS', '2013SS', '2014RS',
            ]
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': [
                '2015RS', '2016RS',
            ]
        },
    ],
    'session_details': {
        '2011 Regular Session': {
            'type': 'primary',
            'start_date': datetime.date(2011, 1, 4),
            'end_date': datetime.date(2011, 3, 9),
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session',
        },
        '2011SS': {
            'type': 'special',
            'start_date': datetime.date(2011, 3, 14),
            'end_date': datetime.date(2011, 4, 6),
            'display_name': '2011 Extraordinary Session',
            '_scraped_name': '2011 Extraordinary Session',
        },
        '2012RS': {
            'type': 'primary',
            'start_date': datetime.date(2012, 1, 3),
            'end_date': datetime.date(2012, 4, 12),
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session',
        },
        '2012SS': {
            'type': 'special',
            'start_date': datetime.date(2012, 4, 16),
            'end_date': datetime.date(2012, 4, 20),
            'display_name': '2012 Extraordinary Session',
            '_scraped_name': '2012 Extraordinary Session',
        },
        '2013RS': {
            'type': 'primary',
            'start_date': datetime.date(2013, 1, 8),
            'end_date': datetime.date(2013, 3, 26),
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Regular Session',
        },
        '2013SS': {
            'type': 'special',
            'start_date': datetime.date(2013, 8, 19),
            'end_date': datetime.date(2013, 8, 19),
            'display_name': '2013 Extraordinary Session',
            '_scraped_name': '2013 Extraordinary Session',
        },
        '2014RS': {
            'type': 'primary',
            'start_date': datetime.date(2014, 1, 7),
            'end_date': datetime.date(2014, 4, 15),
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Regular Session',
        },
        '2015RS': {
            'type': 'primary',
            'start_date': datetime.date(2015, 1, 6),
            'end_date': datetime.date(2015, 3, 25),
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 Regular Session',
        },
        '2016RS': {
            'type': 'primary',
            'start_date': datetime.date(2016, 1, 5),
            'end_date': datetime.date(2016, 4, 12),
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 Regular Session',
        },
    },
    'feature_flags': ['subjects', 'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': [],
}


def session_list():
    sessions = url_xpath('http://www.lrc.ky.gov/legislation.htm',
        '//a[contains(@href, "record.htm")]/text()[normalize-space()]')

    for index, session in enumerate(sessions):
        # Remove escaped whitespace characters.
        sessions[index] = re.sub(r'[\r\n\t]+', '', session)

    return sessions


def extract_text(doc, data):
    return worddata_to_text(data)

