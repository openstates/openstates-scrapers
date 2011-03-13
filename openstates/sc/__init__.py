import datetime

metadata = dict(
    name='South Carolina',
    abbreviation='sc',
    legislature_name='South Carolina Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '119',
         'sessions': ['119'],
         'start_year': 2010, 'end_year': 2012},
        ],
    session_details={
        '119': {'start_date': datetime.date(2010,11,17), 'type': 'primary'},
    }
)
