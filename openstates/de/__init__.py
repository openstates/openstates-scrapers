import datetime
import lxml.html
from billy.utils.fulltext import oyster_text

metadata = dict(
    name='Delaware',
    abbreviation='de',
    capitol_timezone='America/New_York',
    legislature_name='Delaware General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['146',],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '146': {'display_name': '146th General Assembly',
                '_scraped_name': 'GA 146',
               },
    },
    feature_flags=[ 'events', 'influenceexplorer' ],
    _ignored_scraped_sessions=['GA 145', 'GA 144', 'GA 143', 'GA 142',
                               'GA 141', 'GA 140', 'GA 139', 'GA 138']
)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://legis.delaware.gov/',
        "//select[@name='gSession']/option/text()")
    sessions = [ session.strip() for session in sessions ]
    sessions.remove("Session")
    return sessions

@oyster_text
def extract_text(oyster_doc, data):
    if oyster_doc['metadata']['mimetype'] == 'text/html':
        doc = lxml.html.fromstring(data)
        return ' '.join(x.text_content()
                        for x in doc.xpath('//p[@class="MsoNormal"]'))

document_class = dict(
    AWS_PREFIX = 'documents/de/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
