from billy.utils.fulltext import text_after_line_numbers
from .util import get_client, backoff
import lxml.html
from .bills import GABillScraper
from .legislators import GALegislatorScraper
from .committees import GACommitteeScraper

metadata = {
    'name': 'Georgia',
    'abbreviation': 'ga',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Georgia General Assembly',
    'legislature_url': 'http://www.legis.ga.gov/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011_12', '2011_ss']},
        {'name': '2013-2014', 'start_year': 2013, 'end_year': 2014,
         'sessions': ['2013_14']},
        {'name': '2015-2016', 'start_year': 2015, 'end_year': 2016,
         'sessions': ['2015_16']}
     ],
    'session_details': {
        '2015_16': {
            'display_name': '2015-2016 Regular Session',
            '_scraped_name': '2015-2016 Regular Session',
            '_guid': 24
        },
        '2013_14': {
            'display_name': '2013-2014 Regular Session',
            '_scraped_name': '2013-2014 Regular Session',
            '_guid': 23
        },
        '2011_12': {
            'display_name': '2011-2012 Regular Session',
            '_scraped_name': '2011-2012 Regular Session',
            '_guid': 21
        },
        '2011_ss': {
            'display_name': '2011 Special Session',
            '_scraped_name': '2011 Special Session',
            '_guid': 22
        },
    },
    'feature_flags': ['influenceexplorer'],
    '_ignored_scraped_sessions': ['2009-2010 Regular Session',
                                  '2007-2008 Regular Session',
                                  '2005 Special Session',
                                  '2005-2006 Regular Session',
                                  '2004 Special Session',
                                  '2003-2004 Regular Session',
                                  '2001 2nd Special Session',
                                  '2001 1st Special Session',
                                  '2001-2002 Regular Session']
}


def session_list():
    sessions = get_client("Session").service

    # sessions = [x for x in backoff(sessions.GetSessions)['Session']]
    # import pdb; pdb.set_trace()
    # sessions <-- check the Id for the _guid

    sessions = [x['Description'].strip()
                for x in backoff(sessions.GetSessions)['Session']]
    return sessions


def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    lines = doc.xpath('//span/text()')
    headers = ('A\r\nRESOLUTION', 'AN\r\nACT')
    # take off everything before one of the headers
    for header in headers:
        if header in lines:
            text = '\n'.join(lines[lines.index(header)+1:])
            break
    else:
        text = ' '.join(lines)

    return text
