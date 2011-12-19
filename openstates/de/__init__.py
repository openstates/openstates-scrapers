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
        {'name': '146',
         'sessions': ['2011-2012',],
         'start_year': 2011, 'end_year': 2012,},
    ],
    feature_flags=[]
)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://legis.delaware.gov/',
        "//select[@name='gSession']/option/text()")
    sessions = [ session.strip() for session in sessions ]
    sessions.remove("Session")
    return sessions
