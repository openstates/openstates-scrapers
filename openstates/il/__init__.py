metadata = {
    'state_name': 'Illinois',
    'legislature_name': 'The Illinois General Assembly',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_name': 'Senate',
    'lower_title': 'Representative',
    'upper_title': 'Senator',
    'lower_term': 2,
    'upper_term': 4, # technically, in every decennial period, one 
                     # senatorial term is only 2 years. See 
                     # Article IV, Section 2(a) for more information.
    'sessions': ['93','94','95','96'],
    'session_details': {
        '93': {'years': [2003, 2004], 'sub_sessions': [
            'First Special Session', 'Second Special Session', 'Third Special Session', 
            'Fourth Special Session', 'Fifth Special Session', 'Sixth Special Session', 
            'Seventh Special Session', 'Eighth Special Session', 'Ninth Special Session', 
            'Tenth Special Session', 'Eleventh Special Session', 
            'Twelfth Special Session', 'Thirteenth Special Session', 
            'Fourteenth Special Session', 'Fifteenth Special Session', 
            'Sixteenth Special Session', 'Seventeenth Special Session', 
        ]},
        '94': {'years': [2005, 2006], 'sub_sessions': []},
        '95': {'years': [2007, 2008], 'sub_sessions': [
            'First Special Session', 'Second Special Session', 'Third Special Session', 
            'Fourth Special Session', 'Fifth Special Session', 'Sixth Special Session', 
            'Seventh Special Session', 'Eighth Special Session', 'Ninth Special Session', 
            'Tenth Special Session', 'Eleventh Special Session', 
            'Twelfth Special Session', 'Thirteenth Special Session', 
            'Fourteenth Special Session', 'Fifteenth Special Session', 
            'Sixteenth Special Session', 'Seventeenth Special Session', 
            'Eighteenth Special Session', 'Nineteenth Special Session', 
            'Twentieth Special Session', 'Twenty-First Special Session', 
            'Twenty-Second Special Session', 'Twenty-Third Special Session',
            'Twenty-Fourth Special Session', 'Twenty-Fifth Special Session',
            'Twenty-Sixth Special Session', 
        ]},
        '96': {'years': [2009, 2010], 'sub_sessions': [
            'First Special Session', 
        ]},
    }}


year2session = {}
for session,details in metadata['session_details'].items():
    for year in details['years']:
        year2session[year] = session
        year2session[str(year)] = session
