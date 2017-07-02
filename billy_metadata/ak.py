import datetime
import lxml.html

metadata = dict(
    name='Alaska',
    capitol_timezone='America/Anchorage',
    abbreviation='ak',
    legislature_name='Alaska State Legislature',
    legislature_url='http://w3.legis.state.ak.us/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {
            'name': '27',
            'sessions': ['27'],
            'start_year': 2011,
            'end_year': 2012
        },
        {
            'name': '28',
            'sessions': ['28'],
            'start_year': 2013,
            'end_year': 2014
        },
        {
            'name': '29',
            'sessions': ['29'],
            'start_year': 2015,
            'end_year': 2016
        },
        {
            'name': '30',
            'sessions': ['30'],
            'start_year': 2017,
            'end_year': 2018
        },
    ],
    session_details={
        #'26': {'display_name': '26th Legislature',
        #       '_scraped_name': 'The 26th Legislature (2009-2010)'},
        '27': {'display_name': '27th Legislature (2011-2012)',
               '_scraped_name': 'The 27th Legislature (2011-2012)'},
        '28': {'display_name': '28th Legislature (2013-2014)',
               '_scraped_name': 'The 28th Legislature (2013-2014)'},
        '29': {'display_name': '29th Legislature (2015-2016)',
               '_scraped_name': 'The 29th Legislature (2015-2016)'},
        '30': {'display_name': '30th Legislature (2017-2018)',
               '_scraped_name': 'The 30th Legislature (2017-2018)',
               'start_date': datetime.date(2017, 1, 17),
               'end_date': datetime.date(2017, 4, 16)
              },
    },
    _ignored_scraped_sessions=['The 26th Legislature (2009-2010)',
                               'The 25th Legislature (2007-2008)',
                               'The 24th Legislature (2005-2006)',
                               'The 23rd Legislature (2003-2004)',
                               'The 22nd Legislature (2001-2002)',
                               'The 21st Legislature (1999-2000)',
                               'The 20th Legislature (1997-1998)',
                               'The 19th Legislature (1995-1996)',
                               'The 18th Legislature (1993-1994)'],
    feature_flags=['subjects', 'influenceexplorer'],
)
