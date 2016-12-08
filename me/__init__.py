import lxml.html
from .bills import MEBillScraper
from .legislators import MELegislatorScraper
from .committees import MECommitteeScraper

metadata = dict(
    name='Maine',
    capitol_timezone='America/New_York',
    abbreviation='me',
    legislature_name='Maine Legislature',
    legislature_url='http://legislature.maine.gov/',
    chambers={
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2003-2004', 'sessions': ['121'], 'start_year': 2003,
         'end_year': 2004},
        {'name': '2005-2006', 'sessions': ['122'], 'start_year': 2005,
         'end_year': 2006},
        {'name': '2007-2008', 'sessions': ['123'], 'start_year': 2007,
         'end_year': 2008},
        {'name': '2009-2010', 'sessions': ['124'], 'start_year': 2009,
         'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['125'], 'start_year': 2011,
         'end_year': 2012},
        {'name': '2013-2014', 'sessions': ['126'], 'start_year': 2013,
         'end_year': 2014},
        {'name': '2015-2016', 'sessions': ['127'], 'start_year': 2015,
         'end_year': 2016}
    ],
    session_details={
        '121': {'display_name':  '121st Legislature (2003-2004)',
                '_scraped_name': '121st Legislature'},
        '122': {'display_name':  '122nd Legislature (2005-2006)',
                '_scraped_name': '122nd Legislature'},
        '123': {'display_name':  '123rd Legislature (2007-2008)',
                '_scraped_name': '123rd Legislature'},
        '124': {'display_name':  '124th Legislature (2009-2010)',
                '_scraped_name': '124th Legislature'},
        '125': {'display_name':  '125th Legislature (2011-2012)',
                '_scraped_name': '125th Legislature'},
        '126': {'display_name':  '126th Legislature (2013-2014)',
                '_scraped_name': '126th Legislature'},
        '127': {'display_name':  '127th Legislature (2015-2016)',
                '_scraped_name': '127th Legislature'},
    },
    feature_flags=['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=[]

)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions =  url_xpath('http://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp',
                          '//select[@name="LegSession"]/option/text()')
    sessions.remove('jb-Test')
    sessions.remove('2001-2002')
    return sessions

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//div[@class="billtextbody"]')[0].text_content()
