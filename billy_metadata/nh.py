
metadata = {
    'abbreviation': 'nh',
    'name': 'New Hampshire',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'New Hampshire General Court',
    'legislature_url': 'http://www.gencourt.state.nh.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2011-2012', 'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['2013', '2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['2015', '2016'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018', 'sessions': ['2017', '2018'],
         'start_year': 2017, 'end_year': 2018}
        {'name': '2019-2020', 'sessions': ['2019', '2020'],
         'start_year': 2019, 'end_year': 2020}
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2011%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 '_scraped_name': '2011 Session',
                 },
        '2012': {'display_name': '2012 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2012%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 '_scraped_name': '2012 Session',
                 },
        '2013': {'display_name': '2013 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2013%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 # Their dump filename changed, probably just a hiccup.
                 '_scraped_name': '2013',
                 # '_scraped_name': '2013 Session',
                 },
        '2014': {'display_name': '2014 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2014%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 '_scraped_name': '2014 Session',
                 },
        '2015': {'display_name': '2015 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2015%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 '_scraped_name': '2015 Session',
                 },
        '2016': {'display_name': '2016 Regular Session',
                 'zip_url': ('http://gencourt.state.nh.us/downloads/2016%'
                             '20Session%20Bill%20Status%20Tables.zip'),
                 '_scraped_name': '2016 Session',
                 },
        '2017': {'display_name': '2017 Regular Session',
                 '_scraped_name': '2017 Session',
                 },
        '2018': {'display_name': '2018 Regular Session',
                 '_scraped_name': '2018 Session',
                 },
        '2019': {'display_name': '2019 Regular Session',
                 '_scraped_name': '2019 Session',
                 },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2013 Session', '2017 Session Bill Status Tables Link.txt'],
}
