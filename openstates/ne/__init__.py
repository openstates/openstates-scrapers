import datetime

metadata = dict(
    name='Nebraska',
    abbreviation='ne',
    legislature_name='Nebraska Legislature',
#   lower_chamber_name='n/a',
    upper_chamber_name='The Univameral',
#   lower_chamber_title='n/a',
    upper_chamber_title='Senator',
#   lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[
        {'name': '2011-2012', 'sessions': ['102'],
        'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '102': { 'start_date': datetime.date(2011, 1, 5),
        'display_name': '102nd Legislature First Session',}
    },
    feature_flags=[],
)
