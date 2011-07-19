import datetime

metadata = dict(
    name='South Dakota',
    abbreviation='sd',
    legislature_name='South Dakota State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    terms=[
        {'name': '2009-2010', 'start_year': 2009, 'end_year': 2010,
         'sessions': ['2009', '2010']},
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011']},
        ],
    session_details={
        '2010': {'display_name': '2010 Regular Session'},
        '2011': {'start_date': datetime.date(2011, 1, 11),
                 'display_name': '2011 Regular Session',
                },
    },
    feature_flags=['subjects'],
)
