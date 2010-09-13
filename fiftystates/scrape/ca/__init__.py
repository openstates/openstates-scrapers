import datetime

metadata = dict(
    name='California',
    abbreviation='ca',
    legislature_name='California State Legislature',
    lower_chamber_name='Assembly',
    upper_chamber_name='Senate',
    lower_chamber_title='Assemblymember',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        {'name': '20092010',
         'sessions': [
                '20092010',
                '20092010 Special Session 1',
                '20092010 Special Session 2',
                '20092010 Special Session 3',
                '20092010 Special Session 4',
                '20092010 Special Session 5',
                '20092010 Special Session 6',
                '20092010 Special Session 7',
                '20092010 Special Session 8',
                ],
         'start_year': 2009, 'end_year': 2010,
         'start_date': datetime.date(2008, 12, 1),
         },
        ],
    session_details={
        '20092010': {'start_date': datetime.date(2008, 12, 1),
                     'type': 'primary'},
        },
    )
