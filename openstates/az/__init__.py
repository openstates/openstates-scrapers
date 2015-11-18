import datetime
import lxml.html
from billy.utils.fulltext import text_after_line_numbers, pdfdata_to_text
from .bills import AZBillScraper
from .legislators import AZLegislatorScraper
from .committees import AZCommitteeScraper
from .events import AZEventScraper

metadata = dict(
    name='Arizona',
    abbreviation='az',
    legislature_name='Arizona State Legislature',
    legislature_url='http://www.azleg.gov/',
    capitol_timezone='America/Denver',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms = [
        #{'name': '42',
        #    'sessions': [
        #    '42nd-1st-special',
        #    '42nd-2nd-special',
        #    '42nd-1st-regular',
        #    '42nd-3rd-special',
        #    '42nd-4th-special',
        #    '42nd-5th-special',
        #    '42nd-2nd-regular',
        #    '42nd-6th-special',
        #    '42nd-7th-special',

        #    ],
        #    'start_year': 1995, 'end_year': 1996
        #},
       #
        #{'name': '43',
        #    'sessions': [
        #    '43rd-1st-special',
        #    '43rd-1st-regular',
        #    '43rd-2nd-special',
        #    '43rd-3rd-special',
        #    '43rd-4th-special',
        #    '43rd-2nd-regular',
        #    '43rd-5th-special',
        #    '43rd-6th-special',

        #    ],
        #    'start_year': 1997, 'end_year': 1998
        #},
       #
        #{'name': '44',
        #    'sessions': [
        #    '44th-1st-special',
        #    '44th-1st-regular',
        #    '44th-2nd-special',
        #    '44th-3rd-special',
        #    '44th-4th-special',
        #    '44th-2nd-regular',
        #    '44th-5th-special',
        #    '44th-6th-special',
        #    '44th-7th-special',

        #    ],
        #    'start_year': 1999, 'end_year': 2000
        #},
       #
        #{'name': '45',
        #    'sessions': [
        #    '45th-1st-regular',
        #    '45th-1st-special',
        #    '45th-2nd-special',
        #    '45th-3rd-special',
        #    '45th-4th-special',
        #    '45th-2nd-regular',
        #    '45th-5th-special',
        #    '45th-6th-special',

        #    ],
        #    'start_year': 2001, 'end_year': 2002
        #},
       #
        #{'name': '46',
        #    'sessions': [
        #    '46th-1st-special',
        #    '46th-1st-regular',
        #    '46th-2nd-special',
        #    '46th-2nd-regular',

        #    ],
        #    'start_year': 2003, 'end_year': 2004
        #},
       #
        #{'name': '47',
        #    'sessions': [
        #    '47th-1st-regular',
        #    '47th-1st-special',
        #    '47th-2nd-regular',

        #    ],
        #    'start_year': 2005, 'end_year': 2006
        #},
       #
        #{'name': '48',
        #    'sessions': [
        #    '48th-1st-regular',
        #    'misc-technical-session',
        #    '48th-2nd-regular',

        #    ],
        #    'start_year': 2007, 'end_year': 2008
        #},
       #
        {'name': '49',
            'sessions': [
            '49th-1st-special',
            '49th-2nd-special',
            '49th-1st-regular',
            '49th-3rd-special',
            '49th-4th-special',
            '49th-5th-special',
            '49th-6th-special',
            '49th-7th-special',
            '49th-8th-special',
            '49th-2nd-regular',
            '49th-9th-special',

            ],
            'start_year': 2009, 'end_year': 2010
        },

        {'name': '50',
            'sessions': [
            '50th-1st-special',
            '50th-2nd-special',
            '50th-3rd-special',
            '50th-4th-special',
            '50th-1st-regular',
            '50th-2nd-regular',
            ],
            'start_year': 2011, 'end_year': 2012
        },
        {'name': '51',
            'sessions': [
            '51st-1st-regular',
            '51st-1st-special',
            '51st-2nd-regular',
            '51st-2nd-special',
            ],
            'start_year': 2013, 'end_year': 2014
        },
        {
            'name': '52',
            'sessions': [
                '52nd-1st-regular',
                '52nd-1st-special',
                '52nd-2nd-regular',
            ],
            'start_year': 2015,
            'end_year': 2016
        },
        ],
        session_details={
            #'42nd-1st-regular':
            #    {'type': 'primary', 'session_id': 30,
            #    'display_name': '42nd Legislature, 1st Regular Session',
            #    'start_date': datetime.date(1995, 1, 9),
            #    'end_date': datetime.date(1995, 4, 12)},
            #'42nd-1st-special':
            #    {'type': 'special', 'session_id': 31,
            #    'display_name': 'Forty-2nd Legislature, 1st Special Session',
            #    'start_date': datetime.date(1995, 3, 14),
            #    'end_date': datetime.date(1995, 3, 16)},
            #'42nd-2nd-special':
            #    {'type': 'special', 'session_id': 32,
            #    'display_name': 'Forty-2nd Legislature, Second Special Session',
            #    'start_date': datetime.date(1995, 3, 23),
            #    'end_date': datetime.date(1995, 3, 28)},
            #'42nd-3rd-special':
            #    {'type': 'special', 'session_id': 34,
            #    'display_name': '42nd Legislature, 3rd Special Session',
            #    'start_date': datetime.date(1995, 10, 17),
            #    'end_date': datetime.date(1995, 10, 17)},
            #'42nd-4th-special':
            #    {'type': 'special', 'session_id': 35,
            #    'display_name': '42nd Legislature, 4th Special Session',
            #    'start_date': datetime.date(1995, 12, 11),
            #    'end_date': datetime.date(1995, 12, 13)},
            #'42nd-5th-special':
            #    {'type': 'special', 'session_id': 36,
            #    'display_name': '42nd Legislature, 5th Special Session',
            #    'start_date': datetime.date(1996, 3, 13),
            #    'end_date': datetime.date(1996, 3, 25)},
            #'42nd-6th-special':
            #    {'type': 'special', 'session_id': 37,
            #    'display_name': '42nd Legislature, 6th Special Session',
            #    'start_date': datetime.date(1996, 6, 26),
            #    'end_date': datetime.date(1996, 6, 26)},
            #'42nd-7th-special':
            #    {'type': 'special', 'session_id': 38,
            #    'display_name': '42nd Legislature, 7th Special Session',
            #    'start_date': datetime.date(1996, 7, 16),
            #    'end_date': datetime.date(1996, 7, 18)},
            #'42nd-2nd-regular':
            #    {'type': 'primary', 'session_id': 33,
            #    'display_name': '42nd Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(1996, 1, 8),
            #    'end_date': datetime.date(1996, 4, 20)},
            #'43rd-1st-regular':
            #    {'type': 'primary', 'session_id': 50,
            #    'display_name': '43rd Legislature, 1st Regular Session',
            #    'start_date': datetime.date(1997, 1, 13),
            #    'end_date': datetime.date(1997, 4, 21)},
            #'43rd-1st-special':
            #    {'type': 'special', 'session_id': 51,
            #    'display_name': '43rd Legislature, 1st Special Session',
            #    'start_date': datetime.date(1997, 3, 24),
            #    'end_date': datetime.date(1997, 3, 27)},
            #'43rd-2nd-special':
            #    {'type': 'special', 'session_id': 53,
            #    'display_name': '43rd Legislature, 2nd Special Session',
            #    'start_date': datetime.date(1997, 11, 12),
            #    'end_date': datetime.date(1997, 11, 14)},
            #'43rd-3rd-special':
            #    {'type': 'special', 'session_id': 54,
            #    'display_name': '43rd Legislature, 3rd Special Session',
            #    'start_date': datetime.date(1998, 3, 11),
            #    'end_date': datetime.date(1998, 4, 8)},
            #'43rd-4th-special':
            #    {'type': 'special', 'session_id': 55,
            #    'display_name': '43rd Legislature, 4th Special Session',
            #    'start_date': datetime.date(1998, 5, 6),
            #    'end_date': datetime.date(1998, 5, 14)},
            #'43rd-5th-special':
            #    {'type': 'special', 'session_id': 56,
            #    'display_name': '43rd Legislature, 5th Special Session',
            #    'start_date': datetime.date(1998, 7, 7),
            #    'end_date': datetime.date(1998, 7, 8)},
            #'43rd-6th-special':
            #    {'type': 'special', 'session_id': 57,
            #    'display_name': '43rd Legislature, 6th Special Session',
            #    'start_date': datetime.date(1998, 12, 16),
            #    'end_date': datetime.date(1998, 12, 16)},
            #'43rd-2nd-regular':
            #    {'type': 'primary', 'session_id': 52,
            #    'display_name': '43rd Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(1998, 1, 12),
            #    'end_date': datetime.date(1998, 5, 22)},
            #'44th-1st-regular':
            #    {'type': 'primary', 'session_id': 60,
            #    'display_name': '44th Legislature, 1st Regular Session',
            #    'start_date': datetime.date(1999, 1, 11),
            #    'end_date': datetime.date(1999, 5, 7)},
            #'44th-1st-special':
            #    {'type': 'special', 'session_id': 61,
            #    'display_name': '44th Legislature, 1st Special Session',
            #    'start_date': datetime.date(1999, 3, 31),
            #    'end_date': datetime.date(1999, 4, 7)},
            #'44th-2nd-special':
            #    {'type': 'special', 'session_id': 62,
            #    'display_name': '44th Legislature, 2nd Special Session',
            #    'start_date': datetime.date(1999, 6, 22),
            #    'end_date': datetime.date(1999, 6, 22)},
            #'44th-3rd-special':
            #    {'type': 'special', 'session_id': 64,
            #    'display_name': '44th Legislature, 3rd Special Session',
            #    'start_date': datetime.date(1999, 12, 13),
            #    'end_date': datetime.date(1999, 12, 14)},
            #'44th-4th-special':
            #    {'type': 'special', 'session_id': 65,
            #    'display_name': '44th Legislature, 4th Special Session',
            #    'start_date': datetime.date(2000, 2, 14),
            #    'end_date': datetime.date(2000, 2, 17)},
            #'44th-5th-special':
            #    {'type': 'special', 'session_id': 66,
            #    'display_name': '44th Legislature, 5th Special Session',
            #    'start_date': datetime.date(2000, 6, 6),
            #    'end_date': datetime.date(2000, 6, 28)},
            #'44th-6th-special':
            #    {'type': 'special', 'session_id': 68,
            #    'display_name': '44th Legislature, 6th Special Session',
            #    'start_date': datetime.date(2000, 10, 20),
            #    'end_date': datetime.date(2000, 10, 20)},
            #'44th-7th-special':
            #    {'type': 'special', 'session_id': 69,
            #    'display_name': '44th Legislature, 7th Special Session',
            #    'start_date': datetime.date(2000, 11, 13),
            #    'end_date': datetime.date(2000, 12, 4)},
            #'44th-2nd-regular':
            #    {'type': 'primary', 'session_id': 63,
            #    'display_name': '44th Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(2000, 1, 10),
            #    'end_date': datetime.date(2000, 4, 18)},
            #'45th-1st-regular':
            #    {'type': 'primary', 'session_id': 67,
            #    'display_name': '45th Legislature, 1st Regular Session',
            #    'start_date': datetime.date(2001, 1, 8),
            #    'end_date': datetime.date(2001, 5, 10)},
            #'45th-1st-special':
            #    {'type': 'special', 'session_id': 70,
            #    'display_name': '45th Legislature, 1st Special Session',
            #    'start_date': datetime.date(2001, 9, 24),
            #    'end_date': datetime.date(2001, 9, 26)},
            #'45th-2nd-special':
            #    {'type': 'special', 'session_id': 72,
            #    'display_name': '45th Legislature, 2nd Special Session',
            #    'start_date': datetime.date(2001, 11, 13),
            #    'end_date': datetime.date(2001, 12, 19)},
            #'45th-3rd-special':
            #    {'type': 'special', 'session_id': 73,
            #    'display_name': '45th Legislature, 3rd Special Session',
            #    'start_date': datetime.date(2002, 2, 4),
            #    'end_date': datetime.date(2002, 3, 20)},
            #'45th-4th-special':
            #    {'type': 'special', 'session_id': 74,
            #    'display_name': '45th Legislature, 4th Special Session',
            #    'start_date': datetime.date(2002, 4, 1),
            #    'end_date': datetime.date(2002, 5, 23)},
            #'45th-5th-special':
            #    {'type': 'special', 'session_id': 75,
            #    'display_name': '45th Legislature, 5th Special Session',
            #    'start_date': datetime.date(2002, 7, 30),
            #    'end_date': datetime.date(2002, 8, 1)},
            #'45th-6th-special':
            #    {'type': 'special', 'session_id': 77,
            #    'display_name': '45th Legislature, 6th Special Session',
            #    'start_date': datetime.date(2002, 11, 25),
            #    'end_date': datetime.date(2002, 11, 25)},
            #'45th-2nd-regular':
            #    {'type': 'primary', 'session_id': 71,
            #    'display_name': '45th Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(2002, 1, 14),
            #    'end_date': datetime.date(2002, 5, 23)},
            #'46th-1st-regular':
            #    {'type': 'primary', 'session_id': 76,
            #    'display_name': '46th Legislature, 1st Regular Session',
            #    'start_date': datetime.date(2003, 1, 13),
            #    'end_date': datetime.date(2003, 6, 19)},
            #'46th-1st-special':
            #    {'type': 'special', 'session_id': 78,
            #    'display_name': '46th Legislature, 1st Special Session',
            #    'start_date': datetime.date(2003, 3, 17),
            #    'end_date': datetime.date(2003, 3, 17)},
            #'46th-2nd-special':
            #    {'type': 'special', 'session_id': 80,
            #    'display_name': '46th Legislature, 2nd Special Session',
            #    'start_date': datetime.date(2003, 10, 20),
            #    'end_date': datetime.date(2003, 12, 13)},
            #'46th-2nd-regular':
            #    {'type': 'primary', 'session_id': 79,
            #    'display_name': '46th Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(2004, 1, 12),
            #    'end_date': datetime.date(2004, 5, 26)},
            #'47th-1st-regular':
            #    {'type': 'primary', 'session_id': 82,
            #    'display_name': '47th Legislature, 1st Regular Session',
            #    'start_date': datetime.date(2005, 1, 10),
            #    'end_date': datetime.date(2005, 5, 13)},
            #'47th-1st-special':
            #    {'type': 'special', 'session_id': 84,
            #    'display_name': '47th Legislature, 1st Special Session',
            #    'start_date': datetime.date(2006, 1, 24),
            #    'end_date': datetime.date(2006, 3, 6)},
            #'47th-2nd-regular':
            #    {'type': 'primary', 'session_id': 83,
            #    'display_name': '47th Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(2006, 1, 9),
            #    'end_date': datetime.date(2006, 6, 22)},
            #'48th-1st-regular':
            #    {'type': 'primary', 'session_id': 85,
            #    'display_name': '48th Legislature, 1st Regular Session',
            #    'start_date': datetime.date(2007, 1, 8),
            #    'end_date': datetime.date(2007, 6, 20)},
            #'misc-technical-session':
            #    {'type': 'special', 'session_id': 100,
            #    'display_name': 'Miscellaneous Legislature, Technical Session',
            #    'start_date': datetime.date(2008, 1, 1),
            #    'end_date': datetime.date(2008, 12, 31)},
            #'48th-2nd-regular':
            #    {'type': 'primary', 'session_id': 86,
            #    'display_name': '48th Legislature, 2nd Regular Session',
            #    'start_date': datetime.date(2008, 1, 14),
            #    'end_date': datetime.date(2008, 6, 27)},

            '49th-1st-regular':
                {'type': 'primary', 'session_id': 87,
                'display_name': '49th Legislature, 1st Regular Session (2009)',
                'start_date': datetime.date(2009, 1, 12),
                'end_date': datetime.date(2009, 7, 1),
                '_scraped_name': 'Forty-ninth Legislature - First Regular Session',
                },
            '49th-1st-special':
                {'type': 'special', 'session_id': 89,
                'display_name': '49th Legislature, 1st Special Session (2009)',
                'start_date': datetime.date(2009, 1, 28),
                'end_date': datetime.date(2009, 1, 31),
                '_scraped_name': 'Forty-ninth Legislature - First Special Session',
                },
            '49th-2nd-special':
                {'type': 'special', 'session_id': 90,
                'display_name': '49th Legislature, 2nd Special Session (2009)',
                'start_date': datetime.date(2009, 5, 21),
                'end_date': datetime.date(2009, 5, 27),
                '_scraped_name': 'Forty-ninth Legislature - Second Special Session',
                },
            '49th-3rd-special':
                {'type': 'special', 'session_id': 91,
                'display_name': '49th Legislature, 3rd Special Session (2009)',
                'start_date': datetime.date(2009, 7, 6),
                'end_date': datetime.date(2009, 8, 25),
                '_scraped_name': 'Forty-ninth Legislature - Third Special Session',
                },
            '49th-4th-special':
                {'type': 'special', 'session_id': 92,
                'display_name': '49th Legislature, 4th Special Session (2009)',
                'start_date': datetime.date(2009, 11, 17),
                'end_date': datetime.date(2009, 11, 23),
                '_scraped_name': 'Forty-ninth Legislature - Fourth Special Session',
                },
            '49th-5th-special':
                {'type': 'special', 'session_id': 94,
                'display_name': '49th Legislature, 5th Special Session (2009)',
                'start_date': datetime.date(2009, 12, 17),
                'end_date': datetime.date(2009, 12, 19),
                '_scraped_name': 'Forty-ninth Legislature - Fifth Special Session',
                },
            '49th-6th-special':
                {'type': 'special', 'session_id': 95,
                'display_name': '49th Legislature, 6th Special Session (2010)',
                'start_date': datetime.date(2010, 2, 1),
                'end_date': datetime.date(2010, 2, 11),
                '_scraped_name': 'Forty-ninth Legislature - Sixth Special Session',
                },
            '49th-7th-special':
                {'type': 'special', 'session_id': 96,
                'display_name': '49th Legislature, 7th Special Session (2010)',
                'start_date': datetime.date(2010, 3, 8),
                'end_date': datetime.date(2010, 3, 16),
                '_scraped_name': 'Forty-ninth Legislature - Seventh Special Session',
                },
            '49th-8th-special':
                {'type': 'special', 'session_id': 101,
                'display_name': '49th Legislature, 8th Special Session (2010)',
                'start_date': datetime.date(2010, 3, 29),
                'end_date': datetime.date(2010, 4, 1),
                '_scraped_name': 'Forty-ninth Legislature - Eighth Special Session',
                },
            '49th-9th-special':
                {'type': 'special', 'session_id': 103,
                'display_name': '49th Legislature, 9th Special Session (2010)',
                'start_date': datetime.date(2010, 8, 9),
                'end_date': datetime.date(2010, 8, 11),
                '_scraped_name': 'Forty-ninth Legislature - Ninth Special Session',
                },
            '49th-2nd-regular':
                {'type': 'primary', 'session_id': 93,
                'display_name': '49th Legislature, 2nd Regular Session (2010)',
                'start_date': datetime.date(2010, 1, 11),
                'end_date': datetime.date(2010, 4, 29),
                '_scraped_name': 'Forty-ninth Legislature - Second Regular Session',
                },
            '50th-1st-special':
                {'type': 'special', 'session_id': 104,
                'display_name': '50th Legislature, 1st Special Session (2011)',
                'start_date': datetime.date(2011, 1, 19),
                'end_date': datetime.date(2011, 1, 20),
                '_scraped_name': 'Fiftieth Legislature - First Special Session',
                },
            '50th-2nd-special':
                {'type': 'special', 'session_id': 105,
                'display_name': '50th Legislature, 2nd Special Session (2011)',
                'start_date': datetime.date(2011, 2, 14),
                'end_date': datetime.date(2011, 2, 16),
                '_scraped_name': 'Fiftieth Legislature - Second Special Session',
                },
            '50th-3rd-special':
                {'type': 'special', 'session_id': 106,
                'display_name': '50th Legislature, 3rd Special Session (2011)',
                'start_date': datetime.date(2011, 6, 10),
                'end_date': datetime.date(2011, 6, 13),
                '_scraped_name': 'Fiftieth Legislature - Third Special Session',
                },
            '50th-4th-special':
                {'type': 'special', 'session_id': 108,
                'display_name': '50th Legislature, 4th Special Session (2011)',
                'start_date': datetime.date(2011, 11, 1),
                'end_date': datetime.date(2011, 11, 1),
                '_scraped_name': 'Fiftieth Legislature - Fourth Special Session',
                },
            '50th-1st-regular':
                {'type': 'primary', 'session_id': 102,
                'display_name': '50th Legislature, 1st Regular Session (2011)',
                'start_date': datetime.date(2011, 1, 10),
                'end_date': datetime.date(2011,4,20),
                '_scraped_name': 'Fiftieth Legislature - First Regular Session',
                },
            '50th-2nd-regular':
                {'type': 'primary', 'session_id': 107,
                'display_name': '50th Legislature, 2nd Regular Session (2012)',
                '_scraped_name': 'Fiftieth Legislature - Second Regular Session',
                #'start_date': , 'end_date':
                },
            '51st-1st-regular':
                {'type': 'primary', 'session_id': 110,
                 'display_name': '51st Legislature - 1st Regular Session (2013)',
                 '_scraped_name': 'Fifty-first Legislature - First Regular Session'
                },
            '51st-1st-special':
                {'type': 'primary', 'session_id': 111,
                 'display_name': '51st Legislature - 1st Special Session (2013)',
                 '_scraped_name': 'Fifty-first Legislature - First Special Session'
                },
            '51st-2nd-regular':
                {'type': 'primary', 'session_id': 112,
                 'display_name': '51st Legislature - 2nd Regular Session',
                 '_scraped_name': 'Fifty-first Legislature - Second Regular Session'
                },
            '51st-2nd-special':
                {'type': 'special', 'session_id': 113,
                 'display_name': '51st Legislature - 2nd Special Session',
                 '_scraped_name': 'Fifty-first Legislature - Second Special Session'
                },
            '52nd-1st-regular':
                {'type': 'primary', 'session_id': 114,
                 'display_name': '52nd Legislature - 1st Regular Session',
                 '_scraped_name': 'Fifty-second Legislature - First Regular Session'
                },
            '52nd-1st-special': {
                'type': 'special',
                'session_id': 116, # Yes, this is weirdly out of order.
                 'display_name': '52nd Legislature - 1st Special Session',
                 '_scraped_name': 'Fifty-second Legislature - First Special Session',
            },
            '52nd-2nd-regular': {
                'type': 'primary',
                'session_id': 115,
                'display_name': '52nd Legislature - 2nd Regular Session',
                '_scraped_name': 'Fifty-second Legislature - Second Regular Session',
            },
            # get session id from http://www.azleg.gov/SelectSession.asp select
        },
        _ignored_scraped_sessions=[
            'Forty-second Legislature - First Regular Session',
            'Forty-Second Legislature - First Special Session',
            'Forty-Second Legislature - Second Special Session',
            'Forty-second Legislature - Second Regular Session',
            'Forty-second Legislature - Third Special Session',
            'Forty-second Legislature - Fourth Special Session',
            'Forty-second Legislature - Fifth Special Session',
            'Forty-second Legislature - Sixth Special Session',
            'Forty-second Legislature - Seventh Special Session',
            'Forty-third Legislature - First Regular Session',
            'Forty-third Legislature - First Special Session',
            'Forty-third Legislature - Second Regular Session',
            'Forty-third Legislature - Second Special Session',
            'Forty-third Legislature - Third Special Session',
            'Forty-third Legislature - Fourth Special Session',
            'Forty-third Legislature - Fifth Special Session',
            'Forty-third Legislature - Sixth Special Session',
            'Forty-fourth Legislature - First Regular Session',
            'Forty-fourth Legislature - First Special Session',
            'Forty-fourth Legislature - Second Special Session',
            'Forty-fourth Legislature - Second Regular Session',
            'Forty-fourth Legislature - Third Special Session',
            'Forty-fourth Legislature - Fourth Special Session',
            'Forty-fourth Legislature - Fifth Special Session',
            'Forty-fifth Legislature - First Regular Session',
            'Forty-fourth Legislature - Sixth Special Session',
            'Forty-fourth Legislature - Seventh Special Session',
            'Forty-fifth Legislature - First Special Session',
            'Forty-fifth Legislature - Second Regular Session',
            'Forty-fifth Legislature - Second Special Session',
            'Forty-fifth Legislature - Third Special Session',
            'Forty-fifth Legislature - Fourth Special Session',
            'Forty-fifth Legislature - Fifth Special Session',
            'Forty-sixth Legislature - First Regular Session',
            'Forty-fifth Legislature - Sixth Special Session',
            'Forty-sixth Legislature - First Special Session',
            'Forty-sixth Legislature - Second Regular Session',
            'Forty-sixth Legislature - Second Special Session',
            'Forty-seventh Legislature - First Regular Session',
            'Forty-seventh Legislature - Second Regular Session',
            'Forty-seventh Legislature - First Special Session',
            'Forty-eighth Legislature - First Regular Session',
            'Forty-eighth Legislature - Second Regular Session',
            'Fifty-second Legislature - First Special Session',
            'Miscellaneous Legislature - New Member Orientation Session',
            'Miscellaneous Legislature - Technical Session',],
        feature_flags=[ 'events', 'influenceexplorer' ],
    )


def session_list():
    import re
    import requests
    session = requests.Session()

    # idiocy
    data = session.get('http://www.azleg.gov/')
    data = session.get('http://www.azleg.gov/SelectSession.asp')

    doc = lxml.html.fromstring(data.text)
    sessions = doc.xpath('//select/option/text()')
    sessions = [re.sub(r'\(.+$', '', x).strip() for x in sessions]
    return sessions


def extract_text(doc, data):
    if doc['mimetype'] == 'text/html':
        doc = lxml.html.fromstring(data)
        text = doc.xpath('//div[@class="Section2"]')[0].text_content()
        return text
    else:
        return text_after_line_numbers(pdfdata_to_text(data))
