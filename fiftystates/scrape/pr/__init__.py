status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=False,
    legislators=True,
    contributors=['Gabriel J. Perez-Irizarry'],
    notes="""Bills data only available from 2009. Legislator data only available for the current term.
    The documents where the vote data is available are in .doc format and anyways the urls are broken.
    The search page for the bills is sometimes broken for the lower house.""",
)

metadata = dict(
    name='Puerto Rico',
    abbreviation='pr',
    legislature_name='Legislative Assembly of Puerto Rico',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=4,
    terms=[
        {'name': '2009',
         'sessions': ['2009 Regular Session'],
         'start_year': 2009, 'end_year': 2009},
        {'name': '2010',
         'sessions': ['2010 Regular Session'],
         'start_year': 2010, 'end_year': 2010},
         ]
)
