
metadata = {
    'abbreviation': 'wv',
    'capitol_timezone': 'America/New_York',
    'name': 'West Virginia',
    'legislature_name': 'West Virginia Legislature',
    'legislature_url': 'http://www.legis.state.wv.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Delegate'},
    },
    'terms': [
        {'name': '2011-2012',
         'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011', '2012'],
         },
        {'name': '2013-2014',
         'start_year': 2013, 'end_year': 2014,
         'sessions': ['2013', '2014'],
         },
        {'name': '2015-2016',
         'start_year': 2015, 'end_year': 2016,
         'sessions': ['2015', '2016', '20161S'],
         },
        {'name': '2017-2018',
         'start_year': 2017, 'end_year': 2018,
         'sessions': ['2017', '20171S', '20172S', '2018', '20181S', '20182S'],
         },
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2011'
                 },
        '2012': {'display_name': '2012 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2012'
                 },
        '2013': {'display_name': '2013 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2013'
                 },
        '2014': {'display_name': '2014 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2014'
                 },
        '2015': {'display_name': '2015 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2015'
                 },
        '2016': {'display_name': '2016 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2016'
                 },
        '20161S': {'display_name': '2016 First Special Session',
                   'type': 'special',
                   '_scraped_name': '2016',
                   '_special_name': '1X'
                   },
        '2017': {'display_name': '2017 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2017'
                 },
        '20171S': {'display_name': '2017 First Special Session',
                   'type': 'special',
                   },
        '20172S': {'display_name': '2017 Second Special Session',
                   'type': 'special',
                   },
        '2018': {'display_name': '2018 Regular Session',
                 'type': 'primary',
                 '_scraped_name': '2018'
                 },
        '20181S': {'display_name': '2018 First Special Session',
                   'type': 'primary',
                   },
        '20182S': {'display_name': '2018 Second Special Session',
                   'type': 'primary',
                   },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': [
        '2010', '2009', '2008', '2007', '2006',
        '2005', '2004', '2003', '2002', '2001',
        '2000', '1999', '1998', '1997', '1996',
        '1995', '1994', '1993',
    ]
}
