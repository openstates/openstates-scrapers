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
    terms=[],
    session_details={},
)

# Populate 'sessions' and 'session_details'
for year in [y for y in xrange(1987, 2010) if y % 2]:
    term = "%d-%d" % (year, year + 1)
    metadata['terms'].append(dict(
            name=term,
            start_year=year,
            end_year=year + 1,
            sessions=[term]))
    metadata['session_details'][term] = {'type': 'primary'}
