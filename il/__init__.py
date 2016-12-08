from billy.utils.fulltext import text_after_line_numbers
import lxml.html
from .bills import ILBillScraper
from .legislators import ILLegislatorScraper
from .committees import ILCommitteeScraper
from .events import ILEventScraper

metadata = {
    'abbreviation': 'il',
    'name': 'Illinois',
    'legislature_name': 'Illinois General Assembly',
    'legislature_url': 'http://www.ilga.gov/',
    'capitol_timezone': 'America/Chicago',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '93rd', 'sessions': ['93rd', 'Special_93rd'],
         'start_year': 2003, 'end_year': 2004},
        {'name': '94th', 'sessions': ['94th'],
         'start_year': 2005, 'end_year': 2006},
        {'name': '95th', 'sessions': ['95th', 'Special_95th'],
         'start_year': 2007, 'end_year': 2008},
        {'name': '96th', 'sessions': ['96th', 'Special_96th'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '97th', 'sessions': ['97th'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '98th', 'sessions': ['98th'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '99th', 'sessions': ['99th'],
         'start_year': 2015, 'end_year': 2016},
    ],
    'feature_flags': [ 'events', 'influenceexplorer' ],
    'session_details': {
        '99th': {'display_name': '99th Regular Session (2015-2016)',
                 '_scraped_name': '98   (2013-2014)',
                 'speaker': 'Madigan',
                 'president': 'Cullerton',
                 'params': { 'GA': '99', 'SessionId': '88' },
        },
        '98th': {'display_name': '98th Regular Session (2013-2014)',
                 '_scraped_name': '',
                 'speaker': 'Madigan',
                 'president': 'Cullerton',
                 'params': { 'GA': '98', 'SessionId': '85' },

        },
        '97th': {'display_name': '97th Regular Session (2011-2012)',
                 '_scraped_name': '',
                 'params': { 'GA': '97', 'SessionId': '84' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        '96th': {'display_name': '96th Regular Session (2009-2010)',
                 '_scraped_name': '96   (2009-2010)',
                 'params': { 'GA': '96', 'SessionId': '76' },
                 'speaker': 'Madigan',
                 'president': 'Cullerton',

        },
        'Special_96th': {'display_name': '96th Special Session (2009-2010)',
                         'params': { 'GA': '96', 'SessionId': '82', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Cullerton',

        },
        '95th': {'display_name': '95th Regular Session (2007-2008)',
                 '_scraped_name': '95   (2007-2008)',
                 'params': { 'GA': '95', 'SessionId': '51' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        'Special_95th': {'display_name': '95th Special Session (2007-2008)',
                         'params': { 'GA': '95', 'SessionId': '52', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.',

        },
        '94th': {'display_name': '94th Regular Session (2005-2006)',
                 '_scraped_name': '94   (2005-2006)',
                 'params': { 'GA': '94', 'SessionId': '50' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',

        },
        '93rd': {'display_name': '93rd Regular Session (2003-2004)',
                 '_scraped_name': '93   (2003-2004)',
                 'params': { 'GA': '93', 'SessionId': '3' },
                 'speaker': 'Madigan',
                 'president': 'Jones, E.',
        },
        'Special_93rd': {'display_name': '93rd Special Session (2003-2004)',
                         'params': { 'GA': '93', 'SessionID': '14', 'SpecSess': '1' },
                         'speaker': 'Madigan',
                         'president': 'Jones, E.',
        },
    },
    '_ignored_scraped_sessions': [
        '97   (2011-2012)',
        '92   (2001-2002)',
        '91   (1999-2000)',
        '90   (1997-1998)',
        '89   (1995-1996)',
        '88   (1993-1994)',
        '87   (1991-1992)',
        '86   (1989-1990)',
        '85   (1987-1988)',
        '84   (1985-1986)',
        '83   (1983-1984)',
        '82   (1981-1982)',
        '81   (1979-1980)',
        '80   (1977-1978)',
        '79   (1975-1976)',
        '78   (1973-1974)',
        '77   (1971-1972)']

}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://ilga.gov/PreviousGA.asp',
                     '//option/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@class="xsl"]'))
    return text
