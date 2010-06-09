metadata = {
    'state_name': 'West Virginia',
    'legislature_name': 'The West Virginia Legislature',
    'lower_chamber_name': 'House of Delegates',
    'upper_chamber_name': 'Senate',
    'lower_title': 'Delegate',
    'upper_title': 'Senator',
    'lower_term': 2,
    'upper_term': 4,
    'sessions': map(str, xrange(1993, 2010)),
    'session_details': {}}

for year in metadata['sessions']:
    metadata['session_details'][year] = {
        'years': [int(year)],
        'sub_sessions': []}
    for sub in ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th']:
        metadata['session_details'][year]['sub_sessions'].append(
            "%s %s special session" % (year, sub))
