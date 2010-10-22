import datetime

metadata = {
    'name': 'Virginia',
    'abbreviation': 'va',
    'legislature_name': 'Virginia General Assembly',
    'lower_chamber_name': 'House of Delegates',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Delegate',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2009-2011', 'sessions': ['2010', ],
         'start_year': 2009, 'end_year': 2011},
    ],
    'session_details': {
        '2010': {'start_date': datetime.date(2010, 1, 13), 'site_id': '101'},
        '2011': {'start_date': datetime.date(2011, 1, 12), 'site_id': '111'},
    }
}
