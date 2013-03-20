from billy.utils.fulltext import worddata_to_text
from .bills import PRBillScraper
from .legislators import PRLegislatorScraper
from .committees import PRCommitteeScraper
from .events import PREventScraper

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Puerto Rico',
    abbreviation='pr',
    capitol_timezone='America/Puerto_Rico',
    legislature_name='Legislative Assembly of Puerto Rico',
    legislature_url='http://www.oslpr.org/',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2012',
         'sessions': ['2009-2012'],
         'start_year': 2009, 'end_year': 2012},
        {'name': '2013-2016',
         'sessions': ['2013-2016'],
         'start_year': 2013, 'end_year': 2016},
     ],
    session_details={
        '2009-2012': {'display_name': '2009-2012 Session',
                      '_scraped_name': '2009-2012'
                     },
        '2013-2016': {'display_name': '2013-2016 Session',
                      '_scraped_name': '2013-2016'
                     },
    },
    feature_flags=[],
    _ignored_scraped_sessions = ['2005-2008', '2001-2004',
                                 '1997-2000', '1993-1996']
)

def session_list():
    from billy.scrape.utils import url_xpath
    # this URL should work even for future sessions
    return url_xpath('http://www.oslpr.org/legislatura/tl2013/buscar_2013.asp',
                     '//select[@name="URL"]/option/text()')

def extract_text(doc, data):
    return worddata_to_text(data)
