status = dict(
    bills=False,
    bill_versions=False,
    sponsors=False,
    actions=False,
    votes=False,
    legislators=True,
    contributors=['Gabriel J. Perez-Irizarry', 'James Cooper <james@bitmechanic.com>'],
    notes="Legislator data available for only 2009. Oregon does not hold annual sessions.",
)

metadata = dict(
    name='Oregon',
    abbreviation='or',
    legislature_name='Oregon Legislative Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session'],
         'start_year': 2011, 'end_year': 2012},
     ]
)
