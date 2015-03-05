import datetime
from billy.utils.fulltext import pdfdata_to_text, text_after_line_numbers
from .bills import WIBillScraper
from .legislators import WILegislatorScraper
from .committees import WICommitteeScraper
from .events import WIEventScraper

metadata = {
    'abbreviation': 'wi',
    'name': 'Wisconsin',
    'capitol_timezone': 'America/Chicago',
    'legislature_name': 'Wisconsin State Legislature',
    'legislature_url': 'http://legis.wisconsin.gov/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Representative'},
    },
    'terms': [
        #{'name': '2001-2002',
        # 'sessions': ['2001 Regular Session',
        #              'May 2002 Special Session',
        #              'Jan 2002 Special Session',
        #              'May 2001 Special Session'],
        # 'start_year': 2001, 'end_year': 2002},
        #{'name': '2003-2004',
        # 'sessions': ['2003 Regular Session',
        #              'Jan 2003 Special Session'],
        # 'start_year': 2003, 'end_year': 2004},
        #{'name': '2005-2006',
        # 'sessions': ['2005 Regular Session',
        #              'Jan 2005 Special Session'],
        # 'start_year': 2005, 'end_year': 2006 },
        #{'name': '2007-2008',
        # 'sessions': ['March 2008 Special Session',
        #              'April 2008 Special Session',
        #              'Jan 2007 Special Session',
        #              'Oct 2007 Special Session',
        #              'Dec 2007 Special Session',
        #              '2007 Regular Session' ],
        # 'start_year': 2007, 'end_year': 2008 },
        {'name': '2009-2010',
         'sessions': ['June 2009 Special Session',
                      'December 2009 Special Session',
                      '2009 Regular Session'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session', 'January 2011 Special Session',
                      'September 2011 Special Session'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013 Regular Session', 'October 2013 Special Session',
                      'December 2013 Special Session', 'January 2014 Special Session' ],
         'start_year': 2013, 'end_year': 2014},
         {'name': '2015-2016',
         'sessions': ['2015 Regular Session'],
         'start_year': 2015, 'end_year': 2016},
    ],
    'session_details': {
        '2009 Regular Session': {'start_date': datetime.date(2009,1,13),
                                 'end_date': datetime.date(2011,1,3),
                                 'type': 'primary',
                                 'display_name': '2009 Regular Session',
                                 '_scraped_name': '2009 Regular Session',
                                },
        'June 2009 Special Session': {
            'type': 'special', 'site_id': 'jn9',
            'display_name': 'Jun 2009 Special Session',
            '_scraped_name': 'June 2009 Special Session',
        },
        'December 2009 Special Session': {
            'type': 'special', 'site_id': 'de9',
            'display_name': 'Dec 2009 Special Session',
            '_scraped_name': 'December 2009 Special Session',
        },
        '2011 Regular Session': {'start_date': datetime.date(2011,1,11),
                                 'end_date': datetime.date(2013,1,7),
                                 'type': 'primary',
                                 'display_name': '2011 Regular Session',
                                 '_scraped_name': '2011 Regular Session',
                                },
        'January 2011 Special Session': {
            'type': 'special', 'site_id': 'jr1',
            'display_name': 'Jan 2011 Special Session',
            '_scraped_name': 'January 2011 Special Session',
        },
        'September 2011 Special Session': {
            'type': 'special', 'site_id': 'se1',
            'display_name': 'Sep 2011 Special Session',
            '_scraped_name': 'September 2011 Special Session',
        },
        '2013 Regular Session': {'start_date': datetime.date(2013,1,7),
                                 'end_date': datetime.date(2014,1,13),
                                 'type': 'primary',
                                 'display_name': '2013 Regular Session',
                                 '_scraped_name': '2013 Regular Session',
                                },
        'October 2013 Special Session': {
            'type': 'special',
            'display_name': 'Oct 2013 Special Session',
            '_scraped_name': 'October 2013 Special Session',
            'site_id': 'oc3'
        },
        'December 2013 Special Session': {
            'type': 'special',
            'display_name': 'Dec 2013 Special Session',
            '_scraped_name': 'December 2013 Special Session',
            'site_id': 'de3'
        },
        'January 2014 Special Session': {
            'type': 'special',
            'display_name': 'Jan 2014 Special Session',
            '_scraped_name': 'January 2014 Special Session',
            'site_id': 'jr4'
        },
        '2015 Regular Session': {'start_date': datetime.date(2015,1,5),
                                 'end_date': datetime.date(2016,1,11),
                                 'type': 'primary',
                                 'display_name': '2015 Regular Session',
                                 '_scraped_name': '2015 Regular Session',
                                },
    },
    'feature_flags': ['subjects',
    'events', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        'February 2015 Extraordinary Session',
        '2007 Regular Session', 'April 2008 Special Session',
        'March 2008 Special Session', 'December 2007 Special Session',
        'October 2007 Special Session', 'January 2007 Special Session',
        'February 2006 Special Session',
        '2005 Regular Session', 'January 2005 Special Session',
        '2003 Regular Session', 'January 2003 Special Session',
        '2001 Regular Session', 'May 2002 Special Session',
        'January 2002 Special Session', 'May 2001 Special Session',
        '1999 Regular Session', 'May 2000 Special Session',
        'October 1999 Special Session', '1997 Regular Session',
        'April 1998 Special Session', '1995 Regular Session',
        'January 1995 Special Session', 'September 1995 Special Session']
}

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://docs.legis.wisconsin.gov/search',
                         "//select[@name='sessionNumber']/option/text()")
    return [session.strip(' -') for session in sessions]

def extract_text(doc, data):
    is_pdf = (doc['mimetype'] == 'application/pdf' or
              doc['url'].endswith('.pdf'))
    if is_pdf:
        return text_after_line_numbers(pdfdata_to_text(data))
