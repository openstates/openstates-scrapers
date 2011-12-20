import datetime

metadata = {
    'lower_chamber_title': 'Representative',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_title': 'Senator',
    'terms': [
        {
            'end_year': 2010,
            'start_year': 2009,
            'name': '186',
            'sessions': [ '186th' ]
        },
        {
            'end_year': 2012,
            'start_year': 2011,
            'name': '187',
            'sessions': [ '187th' ]
        }
    ],
    'name': 'Massachusetts',
    'upper_chamber_term': 2,
    'abbreviation': 'ma',
    'upper_chamber_name': 'Senate',
    'session_details': {
        '186th': {
            'type': 'primary',
            'display_name': '186th Legislature',
        },
        '187th': {
            'type': 'primary',
            'display_name': '187th Legislature',
        }
    },
    'legislature_name': 'Massachusetts General Court',
    'lower_chamber_term': 2,
    'feature_flags': [],
}

def session_list():
    import re
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://www.malegislature.gov/Bills/Search',
        "//select[@id='Input_GeneralCourtId']/option/text()")
    # Ok, this is actually a mess. Let's clean it up.
    sessions.remove('--Select Value--')
    sessions = [ re.sub("\(.*$", "", session).strip() for session in sessions ]
    return sessions
