import re
import datetime
from billy.utils.fulltext import pdfdata_to_text

metadata = dict(
    name='Wyoming',
    abbreviation='wy',
    legislature_name='Wyoming State Legislature',
    capitol_timezone='America/Denver',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011','2012'],
         'start_year': 2011, 'end_year': 2012,},
        {'name': '2013-2014',
         'sessions': ['2013'],
         'start_year': 2013, 'end_year': 2014,},
    ],
    session_details={
        '2011': {'type': 'primary', 'display_name': '2011 General Session',
                 '_scraped_name': '2011 General Session'
                },
        '2012': {'type': 'special', 'display_name': '2012 Budget Session',
                 '_scraped_name': '2012 Budget Session'
                },
        '2013': {'type': 'primary', 'display_name': '2013 General Session',
                 '_scraped_name': '2013 General Session'
                },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['2010 Budget Session', '2009 General Session',
                               '2008 Budget Session', '2007 General Session',
                               '2006 Budget Session', '2005 General Session',
                               '2004 Budget Session', '2003 General Session',
                               '2002 Budget Session', '2001 General Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://legisweb.state.wy.us/LSOWeb/SessionArchives.aspx',
        "//div[@id='divLegContent']/a/p/text()" )


def extract_text(doc, data):
    return ' '.join(line for line in pdfdata_to_text(data).splitlines()
                    if re.findall('[a-z]', line))
