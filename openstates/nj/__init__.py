import datetime

metadata = dict(
    name='New Jersey',
    abbreviation='nj',
    legislature_name='New Jersey Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='General Assembly',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term="http://en.wikipedia.org/wiki/New_Jersey_Legislature#Elections_and_terms",
    lower_chamber_term=2,
    terms=[
        #{'name': '2000-2001', 'sessions': ['209'],
        # 'start_year': 2000, 'end_year': 2001},
        #{'name': '2002-2003', 'sessions': ['210'],
        # 'start_year': 2002, 'end_year': 2003},
        #{'name': '2004-2005', 'sessions': ['211'],
        # 'start_year': 2004, 'end_year': 2005},
        #{'name': '2006-2007', 'sessions': ['212'],
        # 'start_year': 2006, 'end_year': 2007},
        #{'name': '2008-2009', 'sessions': ['213'],
        # 'start_year': 2008, 'end_year': 2009},
        {'name': '2010-2011', 'sessions': ['214'],
         'start_year': 2010, 'end_year': 2011},
    ],
    session_details={'214': {'start_date': datetime.date(2010, 1, 12),
                             'display_name': '2010-2011 Regular Session'}
                    },
    feature_flags=['subjects'],
)
