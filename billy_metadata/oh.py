import datetime


metadata = dict(
    name='Ohio',
    abbreviation='oh',
    capitol_timezone='America/New_York',
    legislature_name='Ohio General Assembly',
    legislature_url='http://www.legislature.state.oh.us/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'sessions': ['128'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['129'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['130'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['131'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018', 'sessions': ['132'],
         'start_year': 2017, 'end_year': 2018},
        {'name': '2019-2020', 'sessions': ['133'],
         'start_year': 2019, 'end_year': 2020},
    ],
    session_details={
        '128': { 'display_name': '128th Legislature (2009-2010)',
                '_scraped_name': '128',
               },
        '129': {'start_date': datetime.date(2011, 1, 3),
                'display_name': '129th Legislature (2011-2012)',
                '_scraped_name': '129',
               },
        '130': { 'display_name': '130th Legislature (2013-2014)',
                '_scraped_name': '130',
               },
        '131': { 'display_name': '131st Legislature (2015-2016)',
                '_scraped_name': '131',
               },
        '132': { 'display_name': '132st Legislature (2017-2018)',
                '_scraped_name': '132',
               },
        '133': { 'display_name': '133rd Legislature (2019-2020)',
                '_scraped_name': '133',
               },
    },
    feature_flags=['influenceexplorer', 'events'],
    _ignored_scraped_sessions=['127', '126', '125', '124', '123', '122']

)
