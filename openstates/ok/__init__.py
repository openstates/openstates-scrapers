metadata = dict(
    name='Oklahoma',
    abbreviation='ok',
    legislature_name='Oklahoma Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'start_year': 2011,
         'end_year': 2012,
         'sessions': ['2011', '2012']}
        ],
    session_details={
        '2011': {'display_name': '2011 Regular Session',
                 'session_id': '1100',
                 '_scraped_name': '2011 Regular Session'
                },
        '2012': {'display_name': '2012 Regular Session',
                 'session_id': '1200',
                 '_scraped_name': '2012 Regular Session'
                },
    },
    feature_flags=['subjects'],
    _ignored_scraped_sessions=['2010 Regular Session',
                               '2009 Regular Session', '2008 Regular Session',
                               '2007 Regular Session',
                               '2006 Second Special Session',
                               '2006 Regular Session',
                               '2005 Special Session', '2005 Regular Session',
                               '2004 Special Session', '2004 Regular Session',
                               '2003 Regular Session', '2002 Regular Session',
                               '2001 Special Session', '2001 Regular Session',
                               '2000 Regular Session', '1999 Special Session',
                               '1999 Regular Session', '1998 Regular Session',
                               '1997 Regular Session', '1996 Regular Session',
                               '1995 Regular Session',
                               '1994 Second Special Session',
                               '1994 First Special Session',
                               '1994 Regular Session', '1993 Regular Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://webserver1.lsb.state.ok.us/WebApplication2/WebForm1.aspx',
        "//select[@name='cbxSession']/option/text()")
