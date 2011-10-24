import datetime

# most info taken from http://www.kslib.info/constitution/art2.html
# also ballotpedia.org
metadata = dict(
    name='Kansas',
    abbreviation='ks',
    legislature_name='Kansas State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '20092010',
         'sessions': ['2009', '2010'],
         'start_year': 2009, 'end_year': 2010,},
        {'name': '20112012',
         'sessions': ['2011', '2012'],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '2009': {
            'start_date': datetime.date(2009, 1, 12),
            'display_name': '2009 Regular Session',},
        '2010': {
            'start_date': datetime.date(2010, 1, 11),
            'end_date': datetime.date(2010, 5, 28), # extended
            'display_name': '2010 Regular Session',},
        '2011': {
            'start_date': datetime.date(2011, 1, 12),
            'display_name': '2011 Regular Session',
            'type': 'primary',},
        '2012': {
            'start_date': datetime.date(2012, 1, 13),
            'display_name': '2012 Regular Session',},
    },
    feature_flags=[],
)

