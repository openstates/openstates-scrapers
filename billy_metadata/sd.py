import datetime


settings = dict(
    SCRAPELIB_RPM=8,
    SCRAPELIB_RETRY_WAIT=30,
)

metadata = dict(
    name = 'South Dakota',
    abbreviation = 'sd',
    legislature_name = 'South Dakota State Legislature',
    legislature_url = 'http://www.sdlegislature.gov/',
    capitol_timezone = 'America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        {
            'name': '2009-2010',
            'start_year': 2009,
            'end_year': 2010,
            'sessions': ['2009', '2010']
        },
        {
            'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011', '2011s', '2012']
        },
        {
            'name': '2013-2014',
            'start_year': 2013,
            'end_year': 2014,
            'sessions': ['2013', '2014']
        },
        {
            'name': '2015-2016',
            'start_year': 2015,
            'end_year': 2016,
            'sessions': ['2015', '2016']
        },
        {
            'name': '2017-2018',
            'start_year': 2017,
            'end_year': 2018,
            'sessions': ['2017', '2017s', '2018', '2018s']
        },
        {
            'name': '2019-2020',
            'start_year': 2019,
            'end_year': 2020,
            'sessions': ['2019']
        },
    ],
    session_details = {
        '2009': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009 (84th) Session',
        },
        '2010': {
            'display_name': '2010 Regular Session',
            '_scraped_name': '2010 (85th) Session',
        },
        '2011': {
            'start_date': datetime.date(2011, 1, 11),
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 (86th) Session',
        },
        '2011s': {
            'display_name': '2011 Special Session',
            '_scraped_name': '2011 (86th) Special Session',
        },
        '2012': {
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 (87th) Session',
        },
        '2013': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 (88th) Session',
        },
        '2014': {
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 (89th) Session',
        },
        '2015': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015 (90th) Session',
        },
        '2016': {
            'display_name': '2016 Regular Session',
            '_scraped_name': '2016 (91st) Session',
        },
        '2017': {
            'display_name': '2017 Regular Session',
            '_scraped_name': '2017 (92nd) Session',
        },
        '2017s': {
            'display_name': '2017 Special Session',
        },
        '2018': {
            'display_name': '2017 Regular Session',
        },
        '2018s': {
            'display_name': '2018 Special Session',
        },
        '2019': {
            'display_name': '2019 Regular Session',
        },
    },
    feature_flags = ['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions = [
        'Previous Years',
    ],
)
