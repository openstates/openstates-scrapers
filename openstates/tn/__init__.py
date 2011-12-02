import datetime

#start date of each session is the first tuesday in January after new years

metadata = dict(
    name = 'Tennessee',
    abbreviation = 'tn',
    legislature_name = 'Tennessee General Assembly',
    lower_chamber_name = 'House',
    upper_chamber_name = 'Senate',
    lower_chamber_title = 'Represenative',
    upper_chamber_title = 'Senator',
    lower_chamber_term = 2,
    upper_chamber_term = 4,
    terms = [
        {
            'name': '106th General Assembly', 
            'start_year': 2009, 
            'end_year': 2010, 
            'sessions': ['106th Regular Session', '106th Special Session']
        },
        {
            'name': '107th General Assembly', 
            'start_year': 2010, 
            'end_year': 2011, 
            'sessions': ['107th Regular Session']
        }       
    ],
    session_details={
        '107th Regular Session': {
            'start_date': datetime.date(2011, 1, 11),
            'end_date': datetime.date(2012, 1, 10),
            'number': 107,
            'type': 'primary' },
        '106th Regular Session': {
            'start_date': None,
            'end_date': None,
            'number': 106,
            'type': 'primary'},
        '106th Special Session': {
            'start_date': None,
            'end_date': None,
            'number': 106,
            'type': 'special'},
    }
)
