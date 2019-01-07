import datetime

metadata = dict(
    name='Colorado',
    abbreviation='co',
    legislature_name='Colorado General Assembly',
    legislature_url='http://leg.colorado.gov/',
    capitol_timezone='America/Denver',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011A', '2012A', '2012B'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013A', '2014A'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015A', '2016A'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018',
         'sessions': ['2017A', '2017B', '2018A'],
         'start_year': 2017, 'end_year': 2018},
        ],
        {'name': '2019-2020',
         'sessions': ['2019A'],
         'start_year': 2019, 'end_year': 2020},
        ],
    session_details={
        '2011A': {
            'start_date': datetime.date(2011, 1, 26),
            'type': 'primary',
            'display_name': '2011 Regular Session',
            '_scraped_name': "2011 Regular Session"
         },
        '2012A': {
            'start_date': datetime.date(2012, 1, 11),
            'type': 'primary',
            'display_name': '2012 Regular Session',
            '_scraped_name': '2012 Regular Session',
         },
        '2012B': {
            'start_date': datetime.date(2012, 5, 14),
            'type': 'special',
            'display_name': '2012 First Extraordinary Session',
            '_scraped_name': '2012 First Extraordinary Session',
         },
        '2013A': {
            'type': 'primary',
            'display_name': '2013 Regular Session',
            '_scraped_name': '2013 Regular/Special Session',
         },
        '2014A': {
            'type': 'primary',
            'display_name': '2014 Regular Session',
            '_scraped_name': '2014 Regular/Special Session',
         },
        '2015A': {
            'type': 'primary',
            'display_name': '2015 Regular Session',
            '_scraped_name': "2015 Regular Session",
         },
        '2016A': {
            'type': 'primary',
            'display_name': '2016 Regular Session',
            '_scraped_name': "2016 Regular Session",
            '_data_id': '30'
         },
        '2017A': {
            'type': 'primary',
            'display_name': '2017 Regular Session',
            '_scraped_name': "2017 Regular Session",
            '_data_id': '10171'
         },
        '2017B': {
            'type': 'special',
            'display_name': '2017 First Extraordinary Session',
         },
         '2018A': {
             'type': 'primary',
             'display_name': '2018 Regular Session',
             '_scraped_name': "2018 Regular Session",
             '_data_id': '45771'
          },
         '2019A': {
             'type': 'primary',
             'display_name': '2019 Regular Session',
             '_scraped_name': "2019 Regular Session",
             '_data_id': '57701'
          },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=[
        '2013 Legislative Session',
        '2012 First Special Session',
        '2012 Legislative Session',
        '2011 Legislative Session',
        '2010 Legislative Session',
        '2009 Legislative Session',
        '2008 Legislative Session',
        '2007 Legislative Session',
        '2006 First Special Session',
        '2006 Legislative Session',
        '2005 Legislative Session',
        '2004 Legislative Session',
        '2003 Legislative Session',
        '2002 First Special Session',
        '2002 Legislative Session',
        '2001 Second Special Session',
        '2001 First Special Session',
        '2001 Legislative Session',
        '2000 Legislative Session',
        '2010 Regular/Special Session'
    ]
)
