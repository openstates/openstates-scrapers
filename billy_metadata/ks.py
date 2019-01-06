import datetime

# most info taken from http://www.kslib.info/constitution/art2.html
# also ballotpedia.org
metadata = dict(
    name='Kansas',
    abbreviation='ks',
    legislature_name='Kansas State Legislature',
    legislature_url='http://www.kslegislature.org/',
    capitol_timezone='America/Chicago',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012,},
        {'name': '2013-2014',
         'sessions': ['2013-2014'],
         'start_year': 2013, 'end_year': 2014,},
        {'name': '2015-2016',
         'sessions': ['2015-2016'],
         'start_year': 2015, 'end_year': 2016,},
        {'name': '2017-2018',
         'sessions': ['2017-2018'],
         'start_year': 2017, 'end_year': 2018,},
        {'name': '2019-2020',
         'sessions': ['2019-2020'],
         'start_year': 2019, 'end_year': 2020,},
    ],
    session_details={
        '2011-2012': {
            'start_date': datetime.date(2011, 1, 12),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2011_12',
        },
        '2013-2014': {
            'start_date': datetime.date(2013, 1, 14),
            'display_name': '2013-2014 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2013_14',
        },
        '2015-2016': {
            'start_date': datetime.date(2013, 1, 14),
            'display_name': '2015-2016 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2015_16',
        },
        '2017-2018': {
            'start_date': datetime.date(2017, 1, 9),
            'end_date': datetime.date(2017, 5, 19),
            'display_name': '2017-2018 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2017_18',
        },
        '2019-2020': {
            'display_name': '2019-2020 Regular Session',
            'type': 'primary',
        },
    },
    feature_flags=['influenceexplorer'],
)
