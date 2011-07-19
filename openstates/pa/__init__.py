metadata = dict(
    name='Pennsylvania',
    abbreviation='pa',
    legislature_name='Pennsylvania General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        dict(name='2009-2010', start_year=2009,
             end_year=2010,
             sessions=[
                 '2009-2010',
                 '2009-2010 Special Session #1 (Transportation)']),
        dict(name='2011-2012', start_year=2011,
             end_year=2012,
             sessions=[
                 '2011-2012']),
        ],
    session_details={
        '2009-2010': {'type': 'primary',
                      'display_name': '2009-2010 Regular Session',
                     },
        '2009-2010 Special Session #1 (Transportation)': {
            'type': 'special',
            'display_name': '2009-2010, 1st Special Session',
        },
        '2011-2012': {'type': 'primary',
                      'display_name': '2011-2012 Regular Session',
                     },
        },
    feature_flags=['events'],
)
