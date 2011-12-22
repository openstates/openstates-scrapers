import datetime

metadata = dict(
    name='Colorado',
    abbreviation='co',
    legislature_name='Colorado General Assembly',
    lower_chamber_name='House of Representatives',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011A'],
         'start_year': 2011, 'end_year': 2012},
        ],
    session_details={
        '2010A': {'start_date': datetime.date(2010,1,28), 'type': 'primary',
                 'display_name': '2010 Regular Session'}, # XXX: Fixme
        '2011A': {'start_date': datetime.date(2011,1,26), 'type': 'primary',
                 'display_name': '2011 Regular Session'}, # XXX: Fixme
    },
    feature_flags=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    import re
    tags = url_xpath('http://www.leg.state.co.us/clics/clics2011a/cslFrontPages.nsf/PrevSessionInfo?OpenForm',
        "//font/text()")
    sessions = []
    regex = "2[0-9][0-9][0-9]\ .*\ Session"

    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    tags = url_xpath('http://www.leg.state.co.us/CLICS/CLICS2011A/csl.nsf/Home?OpenForm&amp;BaseTarget=Bottom',
        "//font/text()")
    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    return sessions
