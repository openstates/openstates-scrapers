metadata = dict(
    name='Puerto Rico',
    abbreviation='pr',
    legislature_name='Legislative Assembly of Puerto Rico',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=4,
    terms=[
        {'name': '2009-2012',
         'sessions': ['2009-2012'],
         'start_year': 2009, 'end_year': 2012},
     ],
    session_details={
        '2009-2012': {'display_name': '2009-2012 Session'},
    },
    feature_flags=[],
    _ignored_scraped_sessions = [
        '1997',
        '1998',
        '1999',
        '2000',
        '2001',
        '2002',
        '2003',
        '2004',
        '2005',
        '2006',
        '2007',
        '2008',
        '2009',
        '2010',
        '2011'
    ]
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.oslpr.org/library/master.asp?NAV=LEYES',
        "//td[@background='tilepaper-bg.jpg']/ul/li/a/font/b/text()")
