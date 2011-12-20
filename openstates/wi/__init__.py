import datetime

metadata = {
    'abbreviation': 'wi',
    'name': 'Wisconsin',
    'legislature_name': 'Wisconsin State Legislature',
    'lower_chamber_name': 'Assembly',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
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
         'sessions': ['2011 Regular Session', 'January 2011 Special Session'],
         'start_year': 2011, 'end_year': 2011},
    ],
    'session_details': {
        '2009 Regular Session': {'start_date': datetime.date(2009,1,13),
                                 'end_date': datetime.date(2011,1,3),
                                 'type': 'primary',
                                 'display_name': '2009 Regular Session',
                                },
        'June 2009 Special Session': {
            'type': 'special', 'site_id': 'jn9',
            'display_name': 'Jun 2009 Special Session',
        },
        'December 2009 Special Session': {
            'type': 'special', 'site_id': 'de9',
            'display_name': 'Dec 2009 Special Session',
        },
        '2011 Regular Session': {'start_date': datetime.date(2009,1,11),
                                 'end_date': datetime.date(2013,1,7),
                                 'type': 'primary',
                                 'display_name': '2011 Regular Session'
                                },
        'January 2011 Special Session': {
            'type': 'special', 'site_id': 'jr1',
            'display_name': 'Jan 2011 Special Session',
        }
    },
    'feature_flags': ['subjects'],
}
 
def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath( 'http://legis.wisconsin.gov/',
        "//select[@name='session']/option/text()" )
    return [ session.strip() for session in sessions ]
