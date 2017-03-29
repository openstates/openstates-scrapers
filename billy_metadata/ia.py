import datetime

metadata = dict(
    name = 'Iowa',
    abbreviation = 'ia',
    capitol_timezone = 'America/Chicago',
    legislature_name = 'Iowa General Assembly',
    legislature_url = 'https://www.legis.iowa.gov/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011-2012'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013-2014'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015-2016'],
        },
        {
            'name': '2017-2018',
            'start_year': 2017,
            'end_year': 2018,
            'sessions': ['2017-2018'],
        },
    ],
    session_details = {
        '2011-2012': {
            'display_name': '2011-2012 Regular Session',
            '_scraped_name': 'General Assembly: 84',
            'number': '84',
            'start_date': datetime.date(2011, 1, 10),
            'end_date': datetime.date(2013, 1, 13),
        },
        '2013-2014': {
            'display_name': '2013-2014 Regular Session',
            '_scraped_name': 'General Assembly: 85',
            'number': '85',
        },
        '2015-2016': {
            'display_name': '2015-2016 Regular Session',
            '_scraped_name': 'General Assembly: 86',
            'number': '86',
        },
        '2017-2018': {
            'display_name': '2017-2018 Regular Session',
            '_scraped_name': 'General Assembly: 87',
            'number': '87',
        },
    },
    feature_flags = ['events', 'influenceexplorer'],
    _ignored_scraped_sessions = [
        'Legislative Assembly: 86',
        'General Assembly: 83',
        'General Assembly: 82',
        'General Assembly: 81',
        'General Assembly: 80',
        'General Assembly: 79',
        'General Assembly: 79',
        'General Assembly: 78',
        'General Assembly: 78',
        'General Assembly: 77',
        'General Assembly: 77',
        'General Assembly: 76',
    ]
)

