status = dict(
    bills=False,
    bill_versions=False,
    sponsors=False,
    actions=False,
    votes=False,
    legislators=False,
    contributors=['Gabriel J. Perez-Irizarry'],
    notes="",
)

metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    sessions=[],
)

# Populate 'sessions' and 'session_details'
for year in [y for y in xrange(1987, 2010) if y % 2]:
    session = "%d-%d" % (year, year + 1)
    metadata['sessions'].append(dict(
            name=session,
            start_year=year,
            end_year=year + 1,
            sub_sessions=[]))

