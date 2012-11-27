from billy.utils.fulltext import worddata_to_text

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Puerto Rico',
    abbreviation='pr',
    capitol_timezone='America/Puerto_Rico',
    legislature_name='Legislative Assembly of Puerto Rico',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
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

def extract_text(doc, data):
    return worddata_to_text(data)
