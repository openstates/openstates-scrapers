from billy.utils.fulltext import oyster_text
import lxml.html

metadata = dict(
    name='Maine',
    capitol_timezone='America/New_York',
    abbreviation='me',
    legislature_name='Maine Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
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
        '124': {'display_name':  '124th Legislature',
                '_scraped_name': '124th Legislature'},
        '125': {'display_name':  '125th Legislature',
                '_scraped_name': '125th Legislature'},
    },
    feature_flags=['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=['121st Legislature', '122nd Legislature',
                               '123rd Legislature']

)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions =  url_xpath('http://www.mainelegislature.org/LawMakerWeb/advancedsearch.asp',
                          '//select[@name="LegSession"]/option/text()')
    sessions.remove('jb-Test')
    sessions.remove('2001-2002')
    return sessions

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//div[@class="billtextbody"]')[0].text_content()

document_class = dict(
    AWS_PREFIX = 'documents/me/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
