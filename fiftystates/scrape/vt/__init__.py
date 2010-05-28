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
    state_name='Vermont',
    legislature_name='Vermont General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_title='Senator',
    lower_title='Representative',
    upper_term=2,
    lower_term=2,
    sessions=[],
    session_details={},
)

# Populate 'sessions' and 'session_details'
for year in [y for y in xrange(1987, 2010) if y % 2]:
    session = "%d-%d" % (year, year + 1)
    metadata['sessions'].append(session)
    metadata['session_details'][session] = dict(
        years=(year, year + 1),
        sub_sessions=[])
