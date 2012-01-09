import datetime

metadata = dict(
    name='Delaware',
    abbreviation='de',
    legislature_name='Delaware General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['146',],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '146': {'display_name': '146th General Assembly',
                '_scraped_name': 'GA 146',
               },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['GA 145', 'GA 144', 'GA 143', 'GA 142',
                               'GA 141', 'GA 140', 'GA 139', 'GA 138']
)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://legis.delaware.gov/',
        "//select[@name='gSession']/option/text()")
    sessions = [ session.strip() for session in sessions ]
    sessions.remove("Session")
    return sessions
