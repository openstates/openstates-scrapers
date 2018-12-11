import datetime

metadata = {
    'name': 'Florida',
    'abbreviation': 'fl',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'Florida Legislature',
    'legislature_url': 'http://www.leg.state.fl.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011', '2012', '2012B', '2012O'],
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2014', '2014A', '2014O'],
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015', '2015A', '2015B', '2015C', '2016'],
        },
        {
            'name': '2017-2018',
            'start_year': 2017,
            'end_year': 2018,
            'sessions': ['2017', '2017A', '2018'],
        },
        {
            'name': '2019-2020',
            'start_year': 2019,
            'end_year': 2020,
            'sessions': ['2019']
        }
    ],
    'session_details': {
        '2011': {
            'type': 'primary',
            'start_date': datetime.date(2011, 3, 8),
            'end_date': datetime.date(2011, 5, 6),
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        },
        '2012': {
            'type': 'primary',
            'start_date': datetime.date(2012, 1, 10),
            'end_date': datetime.date(2012, 3, 9),
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012',
        },
        '2012B': {
            'type': 'special',
            'start_date': datetime.date(2012, 3, 14),
            'end_date': datetime.date(2012, 3, 28),
            'display_name': '2012 Extraordinary Apportionment Session',
            '_scraped_name': '2012B',
        },
        '2012O': {
            'type': 'organizational',
            'start_date': datetime.date(2012, 11, 20),
            'end_date': datetime.date(2012, 11, 20),
            'display_name': '2012 Organizational Session',
            '_scraped_name': '2012O',
        },
        '2013': {
            'type': 'primary',
            'start_date': datetime.date(2013, 3, 5),
            'end_date': datetime.date(2013, 5, 3),
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        },
        '2014': {
            'type': 'primary',
            'start_date': datetime.date(2014, 3, 4),
            'end_date': datetime.date(2014, 5, 2),
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014',
        },
        '2014A': {
            'type': 'special',
            'start_date': datetime.date(2014, 8, 7),
            'end_date': datetime.date(2014, 8, 11),
            'display_name': '2014 Special Session A',
            '_scraped_name': '2014A',
        },
        '2014O': {
            'type': 'organizational',
            'start_date': datetime.date(2014, 11, 18),
            'end_date': datetime.date(2014, 11, 18),
            '_scraped_name': '2014O',
            'display_name': '2014 Organizational Session',
        },
        '2015': {
            'type': 'primary',
            'start_date': datetime.date(2015, 3, 3),
            'end_date': datetime.date(2015, 5, 1),
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015',
        },
        '2015A': {
            'type': 'special',
            'start_date': datetime.date(2015, 6, 1),
            'end_date': datetime.date(2015, 6, 19),
            'display_name': '2015 Special Session A',
            '_scraped_name': '2015A',
        },
        '2015B': {
            'type': 'special',
            'start_date': datetime.date(2015, 8, 10),
            'end_date': datetime.date(2015, 8, 10),
            'display_name': '2015 Special Session B',
            '_scraped_name': '2015B',
        },
        '2015C': {
            'type': 'special',
            'start_date': datetime.date(2015, 10, 19),
            'end_date': datetime.date(2015, 11, 6),
            'display_name': '2015 Special Session C',
            '_scraped_name': '2015C',
        },
        '2016': {
            'type': 'primary',
            'start_date': datetime.date(2016, 1, 12),
            'end_date': datetime.date(2016, 3, 11),
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016',
        },
        '2017': {
            'type': 'primary',
            'start_date': datetime.date(2017, 3, 7),
            'end_date': datetime.date(2017, 5, 5),
            'display_name': '2017 Regular Session',
            '_scraped_name': '2017',
        },
        '2017A': {
            'type': 'special',
            'display_name': '2017 Special Session',
        },
        '2018': {
            'type': 'primary',
            'display_name': '2018 Regular Session',
        },
        '2019': {
            'type': 'primary',
            'display_name': '2019 Regular Session',
        },
    },
    'feature_flags': ['events', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2010O', '2010A', '2010', '2016O'
    ],
}
