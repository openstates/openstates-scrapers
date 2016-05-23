import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from billy.scrape.utils import url_xpath
from .bills import ARBillScraper
from .legislators import ARLegislatorScraper
from .committees import ARCommitteeScraper
from .events import AREventScraper

metadata = {
    'name': 'Arkansas',
    'abbreviation': 'ar',
    'legislature_name': 'Arkansas General Assembly',
    'legislature_url': 'http://www.arkleg.state.ar.us/',
    'capitol_timezone': 'America/Chicago',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011', '2012F'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2013S1', '2014', '2014F', '2014S2'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015','2015S1', '2016S2', '2016F', '2016S3'],
        },
    ],
    'session_details': {
        '2011': {
            'type': 'primary',
            'start_date': datetime.date(2011, 1, 10),
            'end_date': datetime.date(2011, 4, 27),
            'display_name': '2011 Regular Session',
            '_scraped_name': 'Regular Session, 2011',
            'slug': '2011R',
        },
        '2012F': {
            'type': 'special',
            'start_date': datetime.date(2012, 2, 13),
            'end_date': datetime.date(2012, 3, 9),
            'display_name': '2012 Fiscal Session',
            '_scraped_name': 'Fiscal Session 2012',
            'slug': '2012F',
        },
        '2013': {
            'type': 'primary',
            'start_date': datetime.date(2013, 1, 14),
            'end_date': datetime.date(2013, 5, 17),
            'display_name': '2013 Regular Session',
            '_scraped_name': 'Regular Session, 2013',
            'slug': '2013R',
        },
        '2013S1': {
            'type': 'special',
            'start_date': datetime.date(2013, 10, 17),
            'end_date': datetime.date(2013, 10, 19),
            'display_name': '2013 First Extraordinary Session',
            '_scraped_name': 'First Extraordinary Session, 2013',
            'slug': '2013S1',
        },
        '2014': {
            'type': 'primary',
            'start_date': datetime.date(2014, 2, 10),
            'end_date': datetime.date(2014, 3, 19),
            'display_name': '2014 Regular Session',
            '_scraped_name': 'Regular Session, 2014',
            'slug': '2014R',
        },
        '2014F': {
            'type': 'special',
            'start_date': datetime.date(2014, 2, 10),
            'end_date': datetime.date(2014, 3, 19),
            'display_name': '2014 Fiscal Session',
            '_scraped_name': 'Fiscal Session, 2014',
            'slug': '2014F',
        },
        '2014S2': {
            'type': 'special',
            'start_date': datetime.date(2014, 6, 30),
            'end_date': datetime.date(2014, 7, 2),
            'display_name': '2014 Second Extraordinary Session',
            '_scraped_name': 'Second Extraordinary Session, 2014',
            'slug': '2014S2',
        },
        '2015': {
            'type': 'primary',
            'start_date': datetime.date(2015, 1, 12),
            'end_date': datetime.date(2015, 4, 22),
            'display_name': '2015 Regular Session',
            '_scraped_name': 'Regular Session, 2015',
            'slug': '2015R',
        },
        '2015S1': {
            'type': 'special',
            'start_date': datetime.date(2015, 5, 26),
            'end_date': datetime.date(2015, 5, 28),
            'display_name': '2015 First Extraordinary Session',
            '_scraped_name': 'First Extraordinary Session, 2015',
            'slug': '2015S1',
        },
        '2016S2': {
            'type': 'special',
            'start_date': datetime.date(2016, 4, 6),
            'end_date': datetime.date(2016, 4, 6),
            'display_name': '2016 Second Extraordinary Session',
            '_scraped_name': 'Second Extraordinary Session, 2016',
            'slug': '2016S2',
        },
        '2016F': {
            'type': 'special',
            'start_date': datetime.date(2016, 4, 13),
            'end_date': datetime.date(2016, 5, 9),
            'display_name': '2016 Fiscal Session',
            '_scraped_name': 'Fiscal Session, 2016',
            'slug': '2016F',
        },
        '2016S3': {
            'type': 'special',
            'start_date': datetime.date(2016, 5, 19),
            'display_name': '2016 Third Extraordinary Session',
            '_scraped_name': 'Third Extraordinary Session, 2016',
            'slug': '2016S3',
        },
    },
    'feature_flags': ['influenceexplorer', 'events'],
    '_ignored_scraped_sessions': [
        'Regular Session, 2009',
        'Fiscal Session, 2010',
        'Regular Session, 2007',
        'First Extraordinary Session, 2008',
        'Regular Session, 2005',
        'First Extraordinary Session, 2006 ',
        'Regular Session, 2003 ',
        'First Extraordinary Session, 2003',
        'Second Extraordinary Session, 2003',
        'Regular Session, 2001 ',
        'First Extraordinary Session, 2002',
        'Regular Session, 1999',
        'First Extraordinary Session, 2000',
        'Second Extraordinary Session, 2000',
        'Regular Session, 1997 ',
        'Regular Session, 1995 ',
        'First Extraordinary Session, 1995 ',
        'Regular Session, 1993 ',
        'First Extraordinary Session, 1993 ',
        'Second Extraordinary Session, 1993',
        'Regular Session, 1991',
        'First Extraordinary Session, 1991 ',
        'Second Extraordinary Session, 1991 ',
        'Regular Session, 1989',
        'First Extraordinary Session, 1989',
        'Second Extraordinary Session, 1989',
        'Third Extraordinary Session, 1989 ',
        'Regular Session, 1987 ',
        'First Extraordinary Session, 1987',
        'Second Extraordinary Session, 1987',
        'Third Extraordinary Session, 1987',
        'Fourth Extraordinary Session, 1987',
    ],
}


def session_list():
    links = url_xpath('http://www.arkleg.state.ar.us/assembly/2013/2013R/Pages'
        '/Previous%20Legislatures.aspx', '//a')
    sessions = [a.text_content() for a in links if 'Session' in a.attrib.get(
        'title', '')]
    return sessions


def extract_text(doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))
