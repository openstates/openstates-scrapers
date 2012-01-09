import datetime

metadata = dict(
    name='Wyoming',
    abbreviation='wy',
    legislature_name='Wyoming State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011','2012'],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '2011': {'type': 'primary', 'display_name': '2011 General Session',
                 '_scraped_name': '2011 General Session'
                },
        '2012': {'type': 'special', 'display_name': '2012 Budget Session',
                }
    },
    feature_flags=[],
    _ignored_scraped_sessions=['2010 Budget Session', '2009 General Session',
                               '2008 Budget Session', '2007 General Session',
                               '2006 Budget Session', '2005 General Session',
                               '2004 Budget Session', '2003 General Session',
                               '2002 Budget Session', '2001 General Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://legisweb.state.wy.us/LSOWeb/SessionArchives.aspx',
        "//div[@id='divLegContent']/a/p/text()" )
