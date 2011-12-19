import datetime

metadata = dict(
    name='California',
    abbreviation='ca',
    legislature_name='California State Legislature',
    lower_chamber_name='Assembly',
    upper_chamber_name='Senate',
    lower_chamber_title='Assemblymember',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        {'name': '20092010',
         'sessions': [
                '20092010',
                '20092010 Special Session 1',
                '20092010 Special Session 2',
                '20092010 Special Session 3',
                '20092010 Special Session 4',
                '20092010 Special Session 5',
                '20092010 Special Session 6',
                '20092010 Special Session 7',
                '20092010 Special Session 8',
                ],
         'start_year': 2009, 'end_year': 2010,
         'start_date': datetime.date(2008, 12, 1),
         },
        {'name': '20112012',
         'sessions': ['20112012 Special Session 1', '20112012'],
         'start_year': 2011, 'end_year': 2012,
         'start_date': datetime.date(2010, 12, 6),
         },
        ],
    session_details={
        '20092010': {
            'start_date': datetime.date(2008, 12, 1),
            'display_name': '2009-2010 Regular Session',
            'type': 'primary'
        },
        '20092010 Special Session 1': {
            'type': 'special',
            'display_name': '2009-2010, 1st Special Session',
        },
        '20092010 Special Session 2': {
            'type': 'special',
            'display_name': '2009-2010, 2nd Special Session',
        },
        '20092010 Special Session 3': {
            'type': 'special',
            'display_name': '2009-2010, 3rd Special Session',
        },
        '20092010 Special Session 4': {
            'type': 'special',
            'display_name': '2009-2010, 4th Special Session',
        },
        '20092010 Special Session 5': {
            'type': 'special',
            'display_name': '2009-2010, 5th Special Session',
        },
        '20092010 Special Session 6': {
            'type': 'special',
            'display_name': '2009-2010, 6th Special Session',
        },
        '20092010 Special Session 7': {
            'type': 'special',
            'display_name': '2009-2010, 7th Special Session',
        },
        '20092010 Special Session 8': {
            'type': 'special',
            'display_name': '2009-2010, 8th Special Session',
        },
        '20112012 Special Session 1': {
            'type': 'special',
            'display_name': '2011-2012, 1st Special Session',
        },
        '20112012': {
            'start_date': datetime.date(2010, 12, 6),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary'
        },
    },
    feature_flags=['subjects'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    import re
    sessions = url_xpath('http://www.leginfo.ca.gov/bilinfo.html',
        "//select[@name='sess']/option/text()")
    sessions = [
        re.findall('\(.*\)', session)[0][1:-1] \
        for session in sessions
    ]
    return sessions
