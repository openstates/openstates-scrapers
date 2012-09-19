import datetime
import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

metadata = dict(
    name='Ohio',
    abbreviation='oh',
    capitol_timezone='America/New_York',
    legislature_name='Ohio Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2009-2010', 'sessions': ['128'],
         'start_year': 2009, 'end_year': 2010},
        {'name': '2011-2012', 'sessions': ['129'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '128': { 'display_name': '128th Legislature',
                '_scraped_name': '128',
               },
        '129': {'start_date': datetime.date(2011, 1, 3),
                'display_name': '129th Legislature',
                '_scraped_name': '129',
               },
    },
    feature_flags=[ 'events', 'influenceexplorer' ],
    _ignored_scraped_sessions=['127', '126', '125', '124', '123', '122']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legislature.state.oh.us/search.cfm',
                     '//form[@action="bill_search.cfm"]//input[@type="radio" and @name="SESSION"]/@value')


@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = ' '.join(x.text_content() for x in doc.xpath('//td[@align="LEFT"]'))
    return text

document_class = dict(
    AWS_PREFIX = 'documents/oh/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
