metadata = dict(
    name='New York',
    abbreviation='ny',
    capitol_timezone='America/New_York',
    legislature_name='New York Legislature',

    # unfortunate - there isn't a decent combined site
    legislature_url='http://public.leginfo.state.ny.us/',

    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'Assembly', 'title': 'Assembly Member'},
    },
    terms=[
        dict(name='2009-2010', start_year=2010, end_year=2011,
             sessions=['2009-2010']),
        dict(name='2011-2012', start_year=2011, end_year=2012,
             sessions=['2011-2012']),
        dict(name='2013-2014', start_year=2013, end_year=2014,
             sessions=['2013-2014']),
        dict(name='2015-2016', start_year=2015, end_year=2016,
             sessions=['2015-2016']),
        dict(name='2017-2018', start_year=2017, end_year=2018,
             sessions=['2017-2018']),
        dict(name='2019-2020', start_year=2019, end_year=2020,
             sessions=['2019-2020']),
        ],
    session_details={
        '2009-2010': {
            'display_name': '2009 Regular Session',
            '_scraped_name': '2009',
        },
        '2011-2012': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011',
        },
        '2013-2014': {
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013',
        },
        '2015-2016': {
            'display_name': '2015 Regular Session',
            '_scraped_name': '2015',
        },
        '2017-2018': {
            'display_name': '2017 Regular Session',
            '_scraped_name': '2017',
        },
        '2019-2020': {
            'display_name': '2019 Regular Session',
            '_scraped_name': '2019',
        },
    },
    feature_flags=['subjects', 'events', 'influenceexplorer'],
    _ignored_scraped_sessions=['2009'],

    requests_per_minute=30,
)
