import datetime

metadata = dict(
    name='Utah',
    abbreviation='ut',
    legislature_name='Utah State Legislature',
    lower_chamber_name='House of Representatives',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        dict(name='2011-2012', sessions=['2011'],
             start_year=2011, end_year=2012),
        ],
    session_details={
        '2011': {'start_date': datetime.date(2011, 1, 24),
                 'display_name': '2011 Regular Session',
                },
    },
    feature_flags=['events', 'subjects'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath( 'http://le.utah.gov/',
        "//select[@name='Sess']/option/text()" )
    return [ session.strip() for session in sessions ]
