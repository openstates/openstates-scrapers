import datetime
from billy.utils.fulltext import oyster_text, worddata_to_text

metadata = dict(
    name='Colorado',
    abbreviation='co',
    legislature_name='Colorado General Assembly',
    capitol_timezone='America/Denver',
    lower_chamber_name='House',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011A', '2012A', '2012B'],
         'start_year': 2011, 'end_year': 2012},
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
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions = [
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
    tags = url_xpath('http://www.leg.state.co.us/clics/clics2011a/cslFrontPages.nsf/PrevSessionInfo?OpenForm',
        "//font/text()")
    sessions = []
    regex = "2[0-9][0-9][0-9]\ .*\ Session"

    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    tags = url_xpath('http://www.leg.state.co.us/CLICS/CLICS2011A/csl.nsf/Home?OpenForm&amp;BaseTarget=Bottom',
        "//font/text()")
    for tag in tags:
        sess = re.findall(regex, tag)
        for session in sess:
            sessions.append( session )

    return sessions

@oyster_text
def extract_text(oyster_doc, data):
    return worddata_to_text(data)

document_class = dict(
    AWS_PREFIX = 'documents/co/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
