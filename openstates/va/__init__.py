import datetime

metadata = {
    'name': 'Virginia',
    'abbreviation': 'va',
    'legislature_name': 'Virginia General Assembly',
    'lower_chamber_name': 'House of Delegates',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Delegate',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2009-2011', 'sessions': ['2010', '2011'],
         'start_year': 2010, 'end_year': 2011},
    ],
    'session_details': {
        '2010': {'start_date': datetime.date(2010, 1, 13), 'site_id': '101',
                 'display_name': '2010 Regular Session',
                },
        '2011': {'start_date': datetime.date(2011, 1, 12), 'site_id': '111',
                 'display_name': '2011 Regular Session',
                },
    },
    'feature_flags': ['subjects'],
}

def session_list():

    to_rm = [
        'QUICK LINKS',
        '- - - - - - - - - - - - - -', 'Log in', 'LIS Home',
        'General Assembly Home', '- - - - - - - - - - - - - -',
        'Session Tracking:', 'Bills & Resolutions', 'Members', 'Committees',
        'Meetings', 'Calendars', 'Communications', 'Minutes', 'Statistics',
        'Lobbyist-in-a-Box', 'Personal lists', '- - - - - - - - - - - - - -',
        'Search:', 'Code of Virginia', 'Administrative Code',
        'Bills & Resolutions', 'Summaries', u'OTHER SESSIONS',
        '- - - - - - - - - - - - - -'
    ]

    from billy.scrape.utils import url_xpath
    sessions = url_xpath( 'http://lis.virginia.gov/121/lis.htm',
        "//select[@name='val']/option/text()")
    sessions = [ session.strip() for session in sessions ]

    for x in to_rm:
        sessions.remove( x )

    return sessions
