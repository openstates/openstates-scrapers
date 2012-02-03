import datetime

metadata = dict(
    name='District of Columbia',
    abbreviation='dc',
    legislature_name='Council of the District of Columbia',
#    lower_chamber_name='n/a',
    upper_chamber_name='Council',
#    lower_chamber_title='n/a',
    upper_chamber_title='Councilmember',
#    lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[
        #{'name': '2005-2006', 'sessions': ['16'],
        # 'start_year': 2005, 'end_year': 2006},
        #{'name': '2007-2008', 'sessions': ['17'],
        # 'start_year': 2007, 'end_year': 2008},
        #{'name': '2009-2010', 'sessions': ['18'],
        # 'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['19'],
         'start_year': 2011, 'end_year': 2012},
        ],
    session_details={
        '19': {'display_name': '19th Council Period',
               '_scraped_name': '19',
              }
    },
    feature_flags=[],
    _ignored_scraped_sessions=['18', '17', '16', '15', '14', '13', '12', '11',
                               '10', '9', '8']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://dcclims1.dccouncil.us/lims/list.aspx',
                     '//option/text()')

