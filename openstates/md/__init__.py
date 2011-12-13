import datetime

metadata = dict(
    name='Maryland',
    abbreviation='md',
    legislature_name='Maryland General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Delegates',
    upper_chamber_title='Senator',
    lower_chamber_title='Delegate',
    upper_chamber_term=4,
    lower_chamber_term=4,
    terms=[
        {'name': '2007-2010', 'sessions': ['2007', '2007s1', '2008',
                                           '2009', '2010'],
         'start_year': 2007, 'end_year': 2010},
        {'name': '2011-2014', 'sessions': ['2011'],
         'start_year': 2011, 'end_year': 2014},
    ],
    session_details={
        '2007': {'start_date': datetime.date(2007,1,10),
                 'end_date': datetime.date(2007,4,10),
                 'number': 423,
                 'display_name': '2007 Regular Session',
                 'type': 'primary'},
        '2007s1': {'start_date': datetime.date(2007,10,29),
                   'end_date': datetime.date(2007,11,19),
                   'display_name': '2007, 1st Special Session',
                   'number': 424,
                   'type': 'special'},
        '2008': {'start_date': datetime.date(2008,1,9),
                 'end_date': datetime.date(2008,4,7),
                 'display_name': '2008 Regular Session',
                 'number': 425,
                 'type': 'primary'},
        '2009': {'start_date': datetime.date(2009,1,14),
                 'end_date': datetime.date(2009,4,13),
                 'display_name': '2009 Regular Session',
                 'number': 426,
                 'type': 'primary'},
        '2010': {'start_date': datetime.date(2010,1,13),
                 'end_date': datetime.date(2010,4,12),
                 'number': 427,
                 'display_name': '2010 Regular Session',
                 'type': 'primary'},
        '2011': {'start_date': datetime.date(2011,1,12),
                 'end_date': datetime.date(2011,4,12),
                 'number': 428,
                 'display_name': '2011 Regular Session',
                 'type': 'primary'},
    },
    feature_flags=['subjects'],
)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://mlis.state.md.us/other/PriorSession/index.htm',
                     '(//table)[2]//th/text()')
