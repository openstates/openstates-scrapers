metadata = dict(
    name='Maine',
    abbreviation='me',
    legislature_name='Maine Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    terms=[
        {'name': '2009-2010', 'sessions': ['124'], 'start_year': 2009,
         'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['125'], 'start_year': 2011,
         'end_year': 2012}
    ],
    session_details={
        '124': {'display_name':  '124th Legislature'},
        '125': {'display_name':  '125th Legislature'},
    },
    feature_flags=['subjects'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.maine.gov/legis/senate/Records.html',
        "//td[@class='XSP_MAIN_PANEL']/ul/li/a/text()")
