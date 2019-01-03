import datetime

metadata = dict(
    name='District of Columbia',
    abbreviation='dc',
    capitol_timezone='America/New_York',
    legislature_name='Council of the District of Columbia',
    legislature_url='http://dccouncil.us/',
    chambers = { 'upper': { 'name': 'Council', 'title': 'Councilmember' } },
    terms=[
        #{'name': '2005-2006', 'sessions': ['16'],
        # 'start_year': 2005, 'end_year': 2006},
        #{'name': '2007-2008', 'sessions': ['17'],
        # 'start_year': 2007, 'end_year': 2008},
        #{'name': '2009-2010', 'sessions': ['18'],
        # 'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['19'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['20'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['21'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018', 'sessions': ['22'],
         'start_year': 2017, 'end_year': 2018},
        {'name': '2019-2020', 'sessions': ['23'],
         'start_year': 2019, 'end_year': 2020},
        ],
    session_details={
        '19': {'display_name': '19th Council Period (2011-2012)',
               '_scraped_name': '19' },
        '20': {'display_name': '20th Council Period (2013-2014)',
               '_scraped_name': '20' },
        '21': {'display_name': '21st Council Period (2015-2016)',
               '_scraped_name': '21' },
        '22': {'display_name': '22nd Council Period (2017-2018)',
               '_scraped_name': '22' },
        '23': {'display_name': '23rd Council Period (2019-2020)',
               '_scraped_name': '23' },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['18', '17', '16', '15', '14', '13', '12', '11',
                               '10', '9', '8']

)
