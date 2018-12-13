import datetime

metadata = dict(
    name='South Carolina',
    abbreviation='sc',
    capitol_timezone='America/New_York',
    legislature_name='South Carolina Legislature',
    legislature_url='http://www.scstatehouse.gov/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '119',
         'sessions': ['119'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013-2014'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015-2016'],
         'start_year': 2015, 'end_year': 2016},
        {'name': '2017-2018',
         'sessions': ['2017-2018'],
         'start_year': 2017, 'end_year': 2018},
        {'name': '2019-2020',
         'sessions': ['2019-2020'],
         'start_year': 2019, 'end_year': 2020},
    ],
    session_details={
        '119': {
            'start_date': datetime.date(2010, 11, 17), 'type': 'primary',
            '_scraped_name': '119 - (2011-2012)',
            'display_name': '2011-2012 Regular Session'
        },
        '2013-2014': {
            'start_date': datetime.date(2013, 1, 8), 'type': 'primary',
            '_scraped_name': '120 - (2013-2014)',
            'display_name': '2013-2014 Regular Session',
            '_code': '120',
        },
        '2015-2016': {
            'start_date': datetime.date(2015, 1, 13), 'type': 'primary',
            '_scraped_name': '121 - (2015-2016)',
            'display_name': '2015-2016 Regular Session',
            '_code': '121',
        },
        '2017-2018': {
            'start_date': datetime.date(2017, 1, 10),
            'end_date': datetime.date(2017, 6, 1),
            'type': 'primary',
            '_scraped_name': '122 - (2017-2018)',
            'display_name': '2017-2018 Regular Session',
            '_code': '122',
        },
        '2019-2020': {
            'type': 'primary',
            '_scraped_name': '123 - (2019-2020)',
            'display_name': '2019-2020 Regular Session',
            '_code': '123',
        },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['118 - (2009-2010)', '117 - (2007-2008)',
                               '116 - (2005-2006)', '115 - (2003-2004)',
                               '114 - (2001-2002)', '113 - (1999-2000)',
                               '112 - (1997-1998)', '111 - (1995-1996)',
                               '110 - (1993-1994)', '109 - (1991-1992)',
                               '108 - (1989-1990)', '107 - (1987-1988)',
                               '106 - (1985-1986)', '105 - (1983-1984)',
                               '104 - (1981-1982)', '103 - (1979-1980)',
                               '102 - (1977-1978)', '101 - (1975-1976)']

)

