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
        '2009-2012': {'display_name': '2009-2012 Session',
                      '_scraped_name': '2009-2012'
                     },
    },
    feature_flags=[],
    _ignored_scraped_sessions = ['2005-2008', '2001-2004',
                                 '1997-2000', '1993-1996']
)

def session_list():
    from billy.scrape.utils import url_xpath
    # this URL should work even for future sessions
    return url_xpath('http://www.oslpr.org/legislatura/tl2009/buscar_2009.asp',
                     '//select[@name="URL"]/option/text()')

document_class = dict(
    AWS_PREFIX = 'documents/pr/',
    update_mins = None,
    onchanged = []
)