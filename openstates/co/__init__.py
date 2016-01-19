import datetime
from billy.utils.fulltext import worddata_to_text
from .bills import COBillScraper
from .legislators import COLegislatorScraper
from .committees import COCommitteeScraper
from .votes import COVoteScraper

metadata = dict(
    name='Colorado',
    abbreviation='co',
    legislature_name='Colorado General Assembly',
    legislature_url='http://www.leg.state.co.us/',
    capitol_timezone='America/Denver',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011A', '2012A', '2012B'],
         'start_year': 2011, 'end_year': 2012},
        {'name': '2013-2014',
         'sessions': ['2013A', '2014A'],
         'start_year': 2013, 'end_year': 2014},
        {'name': '2015-2016',
         'sessions': ['2015A', '2016A'],
         'start_year': 2015, 'end_year': 2016},
        ],
    session_details={
        '2011A': {
            'start_date'   : datetime.date(2011,1,26),
            'type'         : 'primary',
             'display_name': '2011 Regular Session',
             '_scraped_name' : "2011 Regular Session"
         },
        '2012A': {
            'start_date'   : datetime.date(2012,1,11),
            'type'         : 'primary',
             'display_name': '2012 Regular Session',
         },
        '2012B': {
            'start_date'   : datetime.date(2012,5,14),
            'type'         : 'special',
             'display_name': '2012 First Extraordinary Session',
         },
        '2013A': {
            'type'         : 'primary',
             'display_name': '2013 Regular Session',
             '_scraped_name': '2013 Regular/Special Session',
         },
        '2014A': {
            'type'         : 'primary',
             'display_name': '2014 Regular Session',
             '_scraped_name': '2014 Regular/Special Session',
         },
        '2015A': {
            'type'         : 'primary',
             'display_name': '2015 Regular Session',
            '_scraped_name': "2015 Regular Session",
         },
        '2016A': {
            'type'         : 'primary',
             'display_name': '2016 Regular Session',
            '_scraped_name': "2016 Regular Session",
         },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions = [
        '2013 Legislative Session',
        '2012 First Special Session',
        '2012 Legislative Session',
        '2011 Legislative Session',
        '2010 Legislative Session',
        '2009 Legislative Session',
        '2008 Legislative Session',
        '2007 Legislative Session',
        '2006 First Special Session',
        '2006 Legislative Session',
        '2005 Legislative Session',
        '2004 Legislative Session',
        '2003 Legislative Session',
        '2002 First Special Session',
        '2002 Legislative Session',
        '2001 Second Special Session',
        '2001 First Special Session',
        '2001 Legislative Session',
        '2000 Legislative Session',
        '2010 Regular/Special Session'
    ]
)

def session_list():
    from billy.scrape.utils import url_xpath
    import re
    tags = url_xpath('http://www.leg.state.co.us/clics/clics2014a/cslFrontPages.nsf/PrevSessionInfo?OpenForm',
        "//font/text()")
    sessions = []
    regex = "2[0-9][0-9][0-9]\ .*\ Session"

    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    tags = url_xpath('http://www.leg.state.co.us/CLICS/CLICS2016A/csl.nsf/Home?OpenForm&amp;BaseTarget=Bottom',
        "//font/text()")
    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    return sessions

def extract_text(doc, data):
    return worddata_to_text(data)
