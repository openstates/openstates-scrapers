import datetime

metadata = dict(
    name='Texas',
    abbreviation='tx',
    legislature_name='Texas Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '81',
         'sessions': ['81', '811'],
         'start_year': 2009, 'end_year': 2010,
         'type': 'primary'},
        {'name': '82',
         'sessions': ['82'],
         'start_year': 2011, 'end_year': 2012,},
        ],
    session_details={
        '81': {'start_date': datetime.date(2009, 1, 13),
               'end_date': datetime.date(2009, 6, 1),
               'type': 'primary'},
        '811': {'start_date': datetime.date(2009, 7, 1),
                'end_date': datetime.date(2009, 7, 10),
                'type': 'special'},
        '82': {'start_date': datetime.date(2011, 1, 11),
               'end_date': None,
               'type': 'primary'},
        },
    )
