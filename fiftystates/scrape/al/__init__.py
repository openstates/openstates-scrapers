import datetime

metadata =  {
    'name': 'Alabama',
    'abbreviation': 'al',
    'legislature_name': 'Alabama Legislature',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 4,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2007-2010',
         'sessions': ['Organization Session 2007',
                      'Regular Session 2007',
                      'Regular Session 2008',
                      'First Special Session 2008',
                      'Regular Session 2009',
                      'First Special Session 2009',
                      'Regular Session 2010'],
         'start_year': 2009,
         'end_year': 2010},
    ],
    'session_details':{
        'Organization Session 2007': {
            'start_date': datetime.date(2007, 1, 9),
            'end_date': datetime.date(2007, 1, 16),
            'type': 'special',
            'internal_id': 1034,
        },
        'Regular Session 2007': {
            'start_date': datetime.date(2007, 3, 6),
            'end_date': datetime.date(2007, 6, 7),
            'type': 'primary',
            'internal_id': 1036,
        },
        'Regular Session 2008': {
            'start_date': datetime.date(2008, 2, 5),
            'end_date': datetime.date(2008, 5, 19),
            'type': 'primary',
            'internal_id': 1047,
        },
        'First Special Session 2008': {
            'start_date': datetime.date(2008, 5, 31),
            'end_date': datetime.date(2008, 5, 27),
            'type': 'special',
            'internal_id': 1048,
        },
        'Regular Session 2009': {
            'start_date': datetime.date(2009, 2, 3),
            'end_date': datetime.date(2009, 5, 15),
            'type': 'primary',
            'internal_id': 1049,
        },
        'First Special Session 2009': {
            'start_date': datetime.date(2009, 8, 14),
            'end_date': datetime.date(2009, 8, 10),
            'type': 'special',
            'internal_id': 1052,
        },
        'Regular Session 2010': {
            'start_date': datetime.date(2010, 1, 12),
            'end_date': datetime.date(2010, 4, 22),
            'type': 'primary',
            'internal_id': 1051,
        },
    }
}
