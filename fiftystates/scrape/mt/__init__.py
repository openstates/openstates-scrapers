status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=True,
    contributors=['James Falcon <therealfalcon@gmail.com>',
                  'Tim Freund <tim@freunds.net>'],
    notes="""
Special sessions aren't yet parsed.  Vote passage determination needs
work (some action names/passage indicators are ambiguous).  Bills published
exclusively in PDF do not have their various versions tracked.""",
    )

metadata = {
    'state_name': 'Montana',
    'legislature_name': 'Montana Legislature',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_title': 'Senator',
    'lower_title': 'Representative',
    'upper_term': 4,
    'lower_term': 2,
    'sessions': ['55th', '56th', '57th', '58th', '59th', '60th', '61st'],
    'session_details': {
        '55th': {'years': [1997, 1998], 'sub_sessions': []},
        '56th': {'years': [1999, 2000],
                 'sub_sessions': ['1999 Special Session', '2000 Special Legislative']},
        '57th': {'years': [2001, 2002],
                 'sub_sessions': ['August 2002 Special Session #1', 'August 2002 Special Session #2']},
        '58th': {'years': [2003, 2004], 'sub_sessions': []},
        '59th': {'years': [2005, 2006], 'sub_sessions': ['December 2005 Special Session']},
        '60th': {'years': [2007, 2008],
                 'sub_sessions': ['2007 September Special Session #1', '2007 September Special Session #2']},
        '61st': {'years': [2009, 2010], 'sub_sessions': []},
        }
    }
