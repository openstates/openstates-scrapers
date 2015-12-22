import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from billy.scrape.utils import url_xpath
from .bills import MOBillScraper
from .legislators import MOLegislatorScraper
from .committees import MOCommitteeScraper
from .votes import MOVoteScraper

metadata = dict(
    name = 'Missouri',
    abbreviation = 'mo',
    legislature_name = 'Missouri General Assembly',
    legislature_url = 'http://www.moga.mo.gov/',
    capitol_timezone = 'America/Chicago',
    chambers = {
        'upper': {
            'name': 'Senate',
            'title': 'Senator'
        },
        'lower': {
            'name': 'House',
            'title': 'Representative'
        },
    },
    terms = [
        {
            'name': '2011-2012',
            'sessions': ['2012'],
            'start_year': 2011,
            'end_year': 2012,
        },
        {
            'name': '2013-2014',
            'sessions': ['2013', '2014'],
            'start_year': 2013,
            'end_year': 2014,
        },
        {
            'name': '2015-2016',
            'sessions': ['2015', '2016'],
            'start_year': 2015,
            'end_year': 2016,
        },
    ],
    # General Assembly sessions convene the Wed. following the first Mon.
    # of January and adjourn May 30.
    # http://www.house.mo.gov/content.aspx?info=/info/howbill.htm
    session_details = {
        '2012': {
            'type': 'primary',
            'start_date': datetime.date(2012,1,4),
            'end_date': datetime.date(2012,5,30),
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 - 96th General Assembly - 2nd Regular Session',
        },
        '2013': {
            'type': 'primary',
            'start_date': datetime.date(2013,1,9),
            'end_date': datetime.date(2013,5,30),
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 - 97th General Assembly - 1st Regular Session',
        },
        '2014': {
            'type': 'primary',
            'start_date': datetime.date(2014,1,8),
            'end_date': datetime.date(2014,5,30),
            'display_name': '2014 Regular Session',
            '_scaped_name': '2014 - 97th General Assembly - 2nd Regular Session',
        },
        '2015': {
            'type': 'primary',
            'start_date': datetime.date(2015,1,7),
            'end_date': datetime.date(2015,5,30),
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 - 98th General Assembly - 1st Regular Session',
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016,1,6),
            'end_date': datetime.date(2016,5,30),
            'display_name': '2016 Regular Session',
        },
    },
    feature_flags = ['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions = [
        '2014 - 97th General Assembly - 2nd Regular Session',
        '2013 - 97th General Assembly - 1st Regular Session',
        '2012 - 96th General Assembly - 2nd Regular Session',
        '2011 - 96th General Assembly - 1st Regular Session',
        '2010 - 95th General Assembly - 2nd Regular Session',
        '2009 - 95th General Assembly - 1st Regular Session',
        '2008 - 94th General Assembly - 2nd Regular Session',
        '2007 - 94th General Assembly - 1st Regular Session',
        '2006 - 93rd General Assembly - 2nd Regular Session',
        '2005 - 93rd General Assembly - 1st Regular Session',
        '2004 - 92nd General Assembly - 2nd Regular Session',
        '2003 - 92nd General Assembly - 1st Regular Session',
        '2002 - 91st General Assembly - 2nd Regular Session',
        '2001 - 91st General Assembly - 1st Regular Session',
        '2000 - 90th General Assembly - 2nd Regular Session',
        '1999 - 90th General Assembly - 1st Regular Session',
        '1998 - 89th General Assembly - 2nd Regular Session',
        '1997 - 89th General Assembly - 1st Regular Session',
        '1996 - 88th General Assembly - 2nd Regular Session',
        '1995 - 88th General Assembly - 1st Regular Session'
    ]
)


def session_list():
    sessions = url_xpath('http://www.senate.mo.gov/pastsessions.htm',
        '//div[@id="list"]/li/a/text()')
    return sessions


def extract_text(doc, data):
    text = pdfdata_to_text(data)
    return text_after_line_numbers(text).encode('ascii', 'ignore')
