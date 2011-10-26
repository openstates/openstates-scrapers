import datetime

metadata = dict(
    name='Wyoming',
    abbreviation='wy',
    legislature_name='Wyoming State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011',],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '2011': {'type': 'primary', 'display_name': '2011 General Session'},
    },
    feature_flags=[],
)
