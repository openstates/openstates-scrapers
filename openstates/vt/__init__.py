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
    terms=[{'name': '2009-2010',
            'start_year': 2009,
            'end_year': 2010,
            'sessions': ['2009-2010']},
           {'name': '2011-2012',
            'start_year': 2011,
            'end_year': 2012,
            'sessions': ['2011-2012']},
           ],
    session_details={'2009-2010': {'type': 'primary',
                                   'display_name': '2009-2010 Regular Session',
                                   '_scraped_name': '2009-2010 Session',
                                  },
                     '2011-2012': {'type': 'primary',
                                   'display_name': '2011-2012 Regular Session',
                                   '_scraped_name': '2011-2012 Session',
                                  },
                     },
    feature_flags=[],
    _ignored_scraped_sessions=['2009 Special Session', '2007-2008 Session',
                               '2005-2006 Session', '2005 Special Session',
                               '2003-2004 Session', '2001-2002 Session',
                               '1999-2000 Session', '1997-1998 Session',
                               '1995-1996 Session', '1993-1994 Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.leg.state.vt.us/ResearchMain.cfm',
        "//div[@id='ddsidebarmenu01']/ul/li/a/text()")
