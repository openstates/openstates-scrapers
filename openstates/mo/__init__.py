import datetime

metadata = dict(
    name='Missouri',
    abbreviation='mo',
    legislature_name='Missouri General Assembly',
    lower_chamber_name='House of Representatives',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011'],
         'start_year': 2011, 'end_year': 2012},
        ],
    session_details={
        '2011': {'start_date': datetime.date(2011,1,26), 'type': 'primary',
                 'display_name': '2011 Regular Session'},
    },
    feature_flags=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.senate.mo.gov/pastsessions.htm',
        "//div[@id='list']/li/a/text()") 

