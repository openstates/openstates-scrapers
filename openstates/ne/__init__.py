import datetime

metadata = dict(
    name='Nebraska',
    abbreviation='ne',
    legislature_name='Nebraska Legislature',
#   lower_chamber_name='n/a',
    upper_chamber_name='The Unicameral',
#   lower_chamber_title='n/a',
    upper_chamber_title='Senator',
#   lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[
        {'name': '2011-2012', 'sessions': ['102', '102S1'],
        'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '102': {
            'start_date': datetime.date(2011, 1, 5),
            'display_name': '102nd Legislature',
            '_scraped_name': '102nd Legislature 1st and Second Sessions',
               },
        '102S1': {
            'display_name': '102nd Legislature, 1st Special Session',
            '_scraped_name': '102nd Legislature 1st Special Session',
            'start_date': datetime.date(2011, 11, 1),
            'end_date': datetime.date(2011, 11, 22)
                 }
        },
    feature_flags=[],
    _ignored_scraped_sessions=['101st Legislature 1st and Second Sessions',
                               '101st Legislature 1st Special Session',
                               '100th Legislature 1st and 2nd Sessions',
                               '100th Leg. First Special Session',
                              ]

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://nebraskalegislature.gov/bills/',
                     "//select[@name='Legislature']/option/text()")[:-1]
