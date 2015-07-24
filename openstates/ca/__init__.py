import datetime
import lxml.html
from .bills import CABillScraper
from .legislators import CALegislatorScraper
from .committees import CACommitteeScraper
from .events import CAEventScraper

settings = dict(SCRAPELIB_RPM=30)

metadata = dict(
    name='California',
    abbreviation='ca',
    capitol_timezone='America/Los_Angeles',
    legislature_name='California State Legislature',
    legislature_url='http://www.legislature.ca.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assemblymember'},
    },
    terms=[
        {'name': '20092010',
         'sessions': [
                '20092010',
                '20092010 Special Session 1',
                '20092010 Special Session 2',
                '20092010 Special Session 3',
                '20092010 Special Session 4',
                '20092010 Special Session 5',
                '20092010 Special Session 6',
                '20092010 Special Session 7',
                '20092010 Special Session 8',
                ],
         'start_year': 2009, 'end_year': 2010,
         'start_date': datetime.date(2008, 12, 1),
         },
        {'name': '20112012',
         'sessions': ['20112012 Special Session 1', '20112012'],
         'start_year': 2011, 'end_year': 2012,
         'start_date': datetime.date(2010, 12, 6),
         },
         {'name': '20132014',
         'sessions': [
                '20132014 Special Session 1', '20132014',
                '20132014 Special Session 2'],
         'start_year': 2013, 'end_year': 2014,
         # 'start_date': datetime.date(2013, ??, ?),
         },
         {'name': '20152016',
         'sessions': [
                      '20152016 Special Session 1',
                      '20152016 Special Session 2',
                      '20152016'],
         'start_year': 2015, 'end_year': 2016,
         },
        ],
    session_details={
        '20092010': {
            'start_date': datetime.date(2008, 12, 1),
            'display_name': '2009-2010 Regular Session',
            'type': 'primary'
        },
        '20092010 Special Session 1': {
            'type': 'special',
            'display_name': '2009-2010, 1st Special Session',
        },
        '20092010 Special Session 2': {
            'type': 'special',
            'display_name': '2009-2010, 2nd Special Session',
        },
        '20092010 Special Session 3': {
            'type': 'special',
            'display_name': '2009-2010, 3rd Special Session',
        },
        '20092010 Special Session 4': {
            'type': 'special',
            'display_name': '2009-2010, 4th Special Session',
        },
        '20092010 Special Session 5': {
            'type': 'special',
            'display_name': '2009-2010, 5th Special Session',
        },
        '20092010 Special Session 6': {
            'type': 'special',
            'display_name': '2009-2010, 6th Special Session',
        },
        '20092010 Special Session 7': {
            'type': 'special',
            'display_name': '2009-2010, 7th Special Session',
        },
        '20092010 Special Session 8': {
            'type': 'special',
            'display_name': '2009-2010, 8th Special Session',
        },
        '20112012 Special Session 1': {
            'type': 'special',
            'display_name': '2011-2012, 1st Special Session',
        },
        '20112012': {
            'start_date': datetime.date(2010, 12, 6),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary'
        },
        '20132014': {
            # 'start_date': datetime.date(2013, ?, ?),
            'display_name': '2013-2014 Regular Session',
            'type': 'primary'
        },
        '20132014 Special Session 1': {
            # 'start_date': datetime.date(2013, ?, ?),
            'display_name': '2013-2014, 1st Special Session',
            'type': 'special'
        },
        '20132014 Special Session 2': {
            # 'start_date': datetime.date(2013, ?, ?),
            'display_name': '2013-2014, 2nd Special Session',
            'type': 'special'
        },
        '20152016': {
            # 'start_date': datetime.date(2013, ?, ?),
            'display_name': '2015-2016 Regular Session',
            '_scraped_name': "2015-2016",
            'type': 'primary'
        },
        '20152016 Special Session 1': {
            'display_name': '2015-2016, 1st Special Session',
            'type': 'special'
        },
        '20152016 Special Session 2': {
            'display_name': '2015-2016, 2nd Special Session',
            'type': 'special'
        },
    },
    feature_flags=['subjects', 'influenceexplorer'],

    _ignored_scraped_sessions = [
        '2013-2014',
        '2011-2012',
        '2009-2010',
        '2007-2008',
        '2005-2006',
        '2003-2004',
        '2001-2002',
        '1999-2000',
        '1997-1998',
        '1995-1996',
        '1993-1994'
        ]
)


def session_list():
    from billy.scrape.utils import url_xpath
    import re
    sessions = url_xpath('http://www.leginfo.ca.gov/bilinfo.html',
        "//select[@name='sess']/option/text()")
    sessions = [
        re.findall('\(.*\)', session)[0][1:-1] \
        for session in sessions
    ]
    return sessions


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    divs_to_try = ['//div[@id="bill"]', '//div[@id="bill_all"]']
    for xpath in divs_to_try:
        div = doc.xpath(xpath)
        if div:
            return div[0].text_content()
