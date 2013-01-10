import re
import lxml.html

metadata = dict(
    name='Oregon',
    abbreviation='or',
    capitol_timezone='America/Los_Angeles',
    legislature_name='Oregon Legislative Assembly',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session',
                      '2012 Regular Session',
                      '2012 Special Session' ],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '2011 Regular Session': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session (February 1 - June 30)',
            'slug': '11reg',
        },
        '2012 Regular Session': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session (February 1 - March 5)',
            'slug': '12reg',
        },
        '2012 Special Session' : {
            'display_name': '2012 Speical Session',
            '_scraped_name': '2012 Special Session (December 14)',
            'slug': '12s',
        }
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['2010 Special Session (February 1 - February 25)',
                               '2009 Regular Session (January 12 - June 29)',
                               '2008 Special Session (February 4 - February 22)',
                               '2007 Regular Session (January 8 - June 28)',
                               '2006 Special Session (April 20)',
                               '2005 Regular Session (January 10 - August 5)',
                               '2003 Regular Session (January 13- August 27)',
                               '2002 Special Sessions',
                               '2001 Regular Session (January 8 - July 7)',
                               '1999 Regular Session (January 11 - July 24)',
                               '1997 Regular Session (January 13 - July 5)',
                               '1996 Special Session (February 1-2)',
                               '1995 Special Session (July 28 - August 2)',
                               '1995 Regular Session (January 9 - June 10)']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return [x.strip() for x in
            url_xpath('http://www.leg.state.or.us/bills_laws/billsinfo.htm',
                     '//a[contains(@href, "measures")]/text()')]

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    lines = doc.xpath('//pre/text()')[0].splitlines()
    text = ' '.join(line for line in lines
                    if not re.findall('Page \d+$', line))
    return text
