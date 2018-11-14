import datetime

# start date of each session is the first tuesday in January after new years

metadata = dict(
    name='Tennessee',
    abbreviation='tn',
    capitol_timezone='America/Chicago',
    legislature_name='Tennessee General Assembly',
    legislature_url='http://www.legislature.state.tn.us/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        # {'name': '106', 'sessions': ['106'],
        #     'start_year': 2009, 'end_year': 2010},
        {'name': '107', 'sessions': ['107'],
            'start_year': 2011, 'end_year': 2012},
        {'name': '108', 'sessions': ['108'],
            'start_year': 2013, 'end_year': 2014},
        {'name': '109', 'sessions': ['109', '109s1', '109s2'],
            'start_year': 2015, 'end_year': 2016},
        {'name': '110', 'sessions': ['110'],
            'start_year': 2017, 'end_year': 2018},
        {'name': '111', 'sessions': ['111'],
            'start_year': 2019, 'end_year': 2020},
    ],
    session_details={
        '111': {
            "_scraped_name": "111th General Assembly",
            "type": "primary",
            "display_name": "111th Regular Session (2019-2020)",
            'start_date': datetime.date(2019, 1, 9),
        },
        '110': {
            'type': 'primary',
            'display_name': '110th Regular Session (2017-2018)',
            '_scraped_name': '110th General Assembly'
        },
        '109s2': {
            'type': 'special',
            'start_date': datetime.date(2016, 9, 12),
            'end_date': datetime.date(2016, 9, 14),
            'display_name': '109th Second Extraordinary Session (September 2016)',
            '_scraped_name': '2nd Extraordinary Session (September 2016)'},
        '109s1': {
            'type': 'special',
            'start_date': datetime.date(2016, 2, 1),
            'end_date': datetime.date(2016, 2, 29),
            'display_name': '109th First Extraordinary Session (February 2016)',
            '_scraped_name': '1st Extraordinary Session (February 2015)'},
        '109': {
            'type': 'primary',
            'display_name': '109th Regular Session (2015-2016)',
            '_scraped_name': '109th General Assembly'},
        '108': {
            'type': 'primary',
            'display_name': '108th Regular Session (2013-2014)',
            '_scraped_name': '108th General Assembly'},
        '107': {
            'start_date': datetime.date(2011, 1, 11),
            'end_date': datetime.date(2012, 1, 10),
            'type': 'primary',
            'display_name': '107th Regular Session (2011-2012)',
            '_scraped_name': '107th General Assembly'},
        # '106': {
        #     'type': 'primary',
        #     'display_name': '106th Regular Session (2009-2010)',
        #     '_scraped_name': '106th General Assembly'},
    },
    feature_flags=['events', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '107th General Assembly',
        '106th General Assembly',
        '105th General Assembly', '104th General Assembly',
        '103rd General Assembly', '102nd General Assembly',
        '101st General Assembly', '100th General Assembly',
        '99th General Assembly'
    ]
)
