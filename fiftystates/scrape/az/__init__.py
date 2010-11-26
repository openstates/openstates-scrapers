import datetime
metadata = dict(
    name='Arizona',
    abbreviation='az',
    legislature_name='Arizona State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    terms = [
        {'name': '43',
         'sessions': [
            'Forty-third Legislature - Third Special Session',
            'Forty-third Legislature - Fourth Special Session',
            'Forty-third Legislature - Fifth Special Session', 
            'Forty-third Legislature - Sixth Special Session',
            'Forty-third Legislature - Second Regular Session',
         ],
         'start_year': 1997, 'end_year': 1998
        },
        {'name': '44',
         'sessions': [
            'Forty-fourth Legislature - First Regular Session',
            'Forty-fourth Legislature - First Special Session',
            'Forty-fourth Legislature - Second Special Session',
            'Forty-fourth Legislature - Third Special Session',
            'Forty-fourth Legislature - Fourth Special Session',
            'Forty-fourth Legislature - Fifth Special Session',
            'Forty-fourth Legislature - Sixth Special Session',
            'Forty-fourth Legislature - Seventh Special Session', 
            'Forty-fourth Legislature - Second Regular Session',
         ],
         'start_year': 1999, 'end_year': 2002
        },
        {'name': '45',
         'sessions': [
            'Forty-fifth Legislature - First Regular Session', 
            'Forty-fifth Legislature - First Special Session', 
            'Forty-fifth Legislature - Second Special Session',
            'Forty-fifth Legislature - Third Special Session',
            'Forty-fifth Legislature - Fourth Special Session',
            'Forty-fifth Legislature - Fifth Special Session', 
            'Forty-fifth Legislature - Sixth Special Session',
            'Forty-fifth Legislature - Second Regular Session',
         ],
         'start_year': 2001, 'end_year': 2002
        },
        {'name': '46',
         'sessions': [
            'Forty-sixth Legislature - First Regular Session', 
            'Forty-sixth Legislature - First Special Session', 
            'Forty-sixth Legislature - Second Special Session',
            'Forty-sixth Legislature - Second Regular Session',
         ],
         'start_year': 2003, 'end_year': 2004
        },
        {'name': '47',
         'sessions': [
            'Forty-seventh Legislature - First Regular Session',
            'Forty-seventh Legislature - Second Regular Session',
         ],
         'start_year': 2005, 'end_year': 2006
        },
        {'name': '48',
         'sessions': [
            'Forty-eighth Legislature - First Regular Session',
            'Forty-eighth Legislature - Second Regular Session',
         ],
         'start_year': 2007, 'end_year': 2008
        },
        {'name': '49',
         'sessions': [
            'Forty-ninth Legislature - First Regular Session',
            'Forty-ninth Legislature - First Special Session',
            'Forty-ninth Legislature - Second Special Session',
            'Forty-ninth Legislature - Third Special Session',
            'Forty-ninth Legislature - Fourth Special Session',
            'Forty-ninth Legislature - Fifth Special Session',
            'Forty-ninth Legislature - Sixth Special Session',
            'Forty-ninth Legislature - Seventh Special Session',
            'Forty-ninth Legislature - Eighth Special Session',
            'Forty-ninth Legislature - Ninth Special Session',
            'Forty-ninth Legislature - Second Regular Session',
         ],
         'start_year': 2009, 'end_year': 2010
        },
        ],
        session_details={
        'Forty-second Legislature - First Regular Session':
	        {'type':'primary', 'session_id':30,
	         'start_date': datetime.date(1995,1,9),
	         'end_date': datetime.date(1995,4,12)},
        'Forty-Second Legislature - First Special Session':
	        {'type':'special', 'session_id':31,
	         'start_date': datetime.date(1995,3,14),
	         'end_date': datetime.date(1995,3,16)},
        'Forty-Second Legislature - Second Special Session':
	        {'type':'special', 'session_id':32,
	         'start_date': datetime.date(1995,3,23),
	         'end_date': datetime.date(1995,3,28)},
        'Forty-second Legislature - Third Special Session':
	        {'type':'special', 'session_id':34,
	         'start_date': datetime.date(1995,10,17),
	         'end_date': datetime.date(1995,10,17)},
        'Forty-second Legislature - Fourth Special Session':
	        {'type':'special', 'session_id':35,
	         'start_date': datetime.date(1995,12,11),
	         'end_date': datetime.date(1995,12,13)},
        'Forty-second Legislature - Fifth Special Session':
	        {'type':'special', 'session_id':36,
	         'start_date': datetime.date(1996,3,13),
	         'end_date': datetime.date(1996,3,25)},
        'Forty-second Legislature - Sixth Special Session':
	        {'type':'special', 'session_id':37,
	         'start_date': datetime.date(1996,6,26),
	         'end_date': datetime.date(1996,6,26)},
        'Forty-second Legislature - Seventh Special Session':
	        {'type':'special', 'session_id':38,
	         'start_date': datetime.date(1996,7,16),
	         'end_date': datetime.date(1996,7,18)},
	    'Forty-second Legislature - Second Regular Session':
	        {'type':'primary', 'session_id':33,
	         'start_date': datetime.date(1996,1,8),
	         'end_date': datetime.date(1996,4,20)},
        'Forty-third Legislature - First Regular Session':
	        {'type':'primary', 'session_id':50,
	         'start_date': datetime.date(1997,1,13),
	         'end_date': datetime.date(1997,4,21)},
        'Forty-third Legislature - First Special Session':
	        {'type':'special', 'session_id':51,
	         'start_date': datetime.date(1997,3,24),
	         'end_date': datetime.date(1997,3,27)},
        'Forty-third Legislature - Second Special Session':
	        {'type':'special', 'session_id':53,
	         'start_date': datetime.date(1997,11,12),
	         'end_date': datetime.date(1997,11,14)},
        'Forty-third Legislature - Third Special Session':
	        {'type':'special', 'session_id':54,
	         'start_date': datetime.date(1998,3,11),
	         'end_date': datetime.date(1998,4,8)},
        'Forty-third Legislature - Fourth Special Session':
	        {'type':'special', 'session_id':55,
	         'start_date': datetime.date(1998,5,6),
	         'end_date': datetime.date(1998,5,14)},
        'Forty-third Legislature - Fifth Special Session':
	        {'type':'special', 'session_id':56,
	         'start_date': datetime.date(1998,7,7),
	         'end_date': datetime.date(1998,7,8)},
        'Forty-third Legislature - Sixth Special Session':
	        {'type':'special', 'session_id':57,
	         'start_date': datetime.date(1998,12,16),
	         'end_date': datetime.date(1998,12,16)},
	    'Forty-third Legislature - Second Regular Session':
	        {'type':'primary', 'session_id':52,
	         'start_date': datetime.date(1998,1,12),
	         'end_date': datetime.date(1998,5,22)},
        'Forty-fifth Legislature - First Regular Session':
	        {'type':'primary', 'session_id':67,
	         'start_date': datetime.date(2001,1,8),
	         'end_date': datetime.date(2001,5,10)},
        'Forty-fifth Legislature - First Special Session':
	        {'type':'special', 'session_id':70,
	         'start_date': datetime.date(2001,9,24),
	         'end_date': datetime.date(2001,9,26)},
        'Forty-fifth Legislature - Second Special Session':
	        {'type':'special', 'session_id':72,
	         'start_date': datetime.date(2001,11,13),
	         'end_date': datetime.date(2001,12,19)},
        'Forty-fifth Legislature - Third Special Session':
	        {'type':'special', 'session_id':73,
	         'start_date': datetime.date(2002,2,4),
	         'end_date': datetime.date(2002,3,20)},
        'Forty-fifth Legislature - Fourth Special Session':
	        {'type':'special', 'session_id':74,
	         'start_date': datetime.date(2002,4,1),
	         'end_date': datetime.date(2002,5,23)},
        'Forty-fifth Legislature - Fifth Special Session':
	        {'type':'special', 'session_id':75,
	         'start_date': datetime.date(2002,7,30),
	         'end_date': datetime.date(2002,8,1)},
        'Forty-fifth Legislature - Sixth Special Session':
	        {'type':'special', 'session_id':77,
	         'start_date': datetime.date(2002,11,25),
	         'end_date': datetime.date(2002,11,25)},
        'Forty-fifth Legislature - Second Regular Session':
	        {'type':'primary', 'session_id':71,
	         'start_date': datetime.date(2002,1,14),
	         'end_date': datetime.date(2002,5,23)},	 
        'Forty-sixth Legislature - First Regular Session':
	        {'type':'primary', 'session_id':76,
	         'start_date': datetime.date(2003,1,13),
	         'end_date': datetime.date(2003,6,19)},
        'Forty-sixth Legislature - First Special Session':
	        {'type':'special', 'session_id':78,
	         'start_date': datetime.date(2003,3,17),
	         'end_date': datetime.date(2003,3,17)},
        'Forty-sixth Legislature - Second Special Session':
	        {'type':'special', 'session_id':80,
	         'start_date': datetime.date(2003,10,20),
	         'end_date': datetime.date(2003,12,13)},
	    'Forty-sixth Legislature - Second Regular Session':
	        {'type':'primary', 'session_id':79,
	         'start_date': datetime.date(2004,01,12),
	         'end_date': datetime.date(2004,5,26)},
        'Forty-seventh Legislature - First Regular Session':
	        {'type':'primary', 'session_id':82,
	         'start_date': datetime.date(2005,1,10),
	         'end_date': datetime.date(2005,5,13)},
        'Forty-seventh Legislature - First Special Session':
	        {'type':'special', 'session_id':84,
	         'start_date': datetime.date(2006,1,24),
	         'end_date': datetime.date(2006,3,6)},
        'Forty-eighth Legislature - First Regular Session':
	        {'type':'primary', 'session_id':85,
	         'start_date': datetime.date(2007,1,8),
	         'end_date': datetime.date(2007,6,20)},
        'Forty-eighth Legislature - Second Regular Session':
	        {'type':'primary', 'session_id':86,
	         'start_date': datetime.date(2008,1,14),
	         'end_date': datetime.date(2008,6,27)},
        'Forty-ninth Legislature - First Regular Session':
            {'type': 'primary', 'session_id': 87,
             'start_date': datetime.date(2009,1,12),
             'end_date': datetime.date(2009,7,1)},
        'Forty-ninth Legislature - First Special Session':
            {'type': 'special', 'session_id': 89,
             'start_date': datetime.date(2009,1,28),
             'end_date': datetime.date(2009,1,31)},
        'Forty-ninth Legislature - Second Special Session':
            {'type': 'special', 'session_id': 90,
             'start_date': datetime.date(2009,5,21),
             'end_date': datetime.date(2009,5,27)},
        'Forty-ninth Legislature - Third Special Session':
            {'type': 'special', 'session_id': 91,
             'start_date': datetime.date(2009,7,6),
             'end_date': datetime.date(2009,8,25)},
        'Forty-ninth Legislature - Fourth Special Session':
            {'type': 'special', 'session_id': 92,
             'start_date': datetime.date(2009,11,17),
             'end_date': datetime.date(2009,11,23)},
        'Forty-ninth Legislature - Fifth Special Session':
            {'type': 'special', 'session_id': 94,
             'start_date': datetime.date(2009,12,17),
             'end_date': datetime.date(2009,12,19)},
        'Forty-ninth Legislature - Sixth Special Session':
            {'type': 'special', 'session_id': 95,
             'start_date': datetime.date(2010,2,1),
             'end_date': datetime.date(2010,2,11)},
        'Forty-ninth Legislature - Seventh Special Session':
            {'type': 'special', 'session_id': 96,
             'start_date': datetime.date(2010,3,8),
             'end_date': datetime.date(2010,3,16)},
        'Forty-ninth Legislature - Eighth Special Session':
            {'type': 'special', 'session_id': 101,
             'start_date': datetime.date(2010,3,29),
             'end_date': datetime.date(2010,4,1)},
        'Forty-ninth Legislature - Ninth Special Session':
	        {'type':'special', 'session_id':103,
	         'start_date': datetime.date(2010,8,9),
	         'end_date': datetime.date(2010,8,11)},
        'Forty-ninth Legislature - Second Regular Session':
            {'type': 'primary', 'session_id': 93,
             'start_date': datetime.date(2010,1,11),
             'end_date': datetime.date(2010,4,29)},
    }
    )
