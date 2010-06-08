status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=True,
    legislators=True,
    contributors=['Michael Stephens'],
    notes="",
)

metadata = dict(
    name='Vermont',
    abbreviation='vt',
    legislature_name='Vermont General Assembly',
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
