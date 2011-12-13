metadata = dict(
    name='Nevada',
    abbreviation='nv',
    legislature_name='Nevada Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='Assembly',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        #{'name': '2001-2002', 'start_year': 2001, 'end_year': 2002,
        # 'sessions': ['2001Special17', '2002Special18', '71'],
        #},
        #{'name': '2003-2004', 'start_year': 2003, 'end_year': 2004,
        # 'sessions': ['2003Special19', '2003Special20', '2004Special21', '72']
        #},
        #{'name': '2005-2006', 'start_year': 2005, 'end_year': 2006,
        # 'sessions': ['2005Special22', '73']
        #},
        #{'name': '2007-2008', 'start_year': 2007, 'end_year': 2008,
        # 'sessions': ['2007Special23', '2008Special24', '2008Special25', '74']
        #},
        {'name': '2009-2010', 'start_year': 2009, 'end_year': 2010,
         'sessions': ['2010Special26', '75']
        },
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['76']
        }
    ],
    session_details={
        '2010Special26': {'type':'special',
                          'display_name': '26th Special Session (2010)'},
        '75': {'type': 'primary',
               'display_name': '2009 Regular Session'},
        '76': {'type': 'primary',
               'display_name': '2011 Regular Session'},
    },
    feature_flags=['subjects'],
)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.leg.state.nv.us/Session/',
                     '//string(*[@class="MainHeading"])')]
