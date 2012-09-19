import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

settings = dict(SCRAPELIB_TIMEOUT=600)

metadata = dict(
    name='Alaska',
    capitol_timezone='America/Anchorage',
    abbreviation='ak',
    legislature_name='The Alaska State Legislature',
    lower_chamber_name='House',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        dict(name='26', sessions=['26'],
             start_year=2009, end_year=2010),
        dict(name='27', sessions=['27'],
             start_year=2011, end_year=2012),
    ],
    session_details={
        '26': {'display_name': '26th Legislature',
               '_scraped_name': 'The 26th Legislature (2009-2010)'},
        '27': {'display_name': '27th Legislature',
               '_scraped_name': 'The 27th Legislature (2011-2012)'},
    },
    _ignored_scraped_sessions=['The 25th Legislature (2007-2008)',
                               'The 24th Legislature (2005-2006)',
                               'The 23rd Legislature (2003-2004)',
                               'The 22nd Legislature (2001-2002)',
                               'The 21st Legislature (1999-2000)',
                               'The 20th Legislature (1997-1998)',
                               'The 19th Legislature (1995-1996)',
                               'The 18th Legislature (1993-1994)'],
    feature_flags=['subjects', 'influenceexplorer'],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.ak.us/basis/start.asp',
                     '(//ul)[last()]/li/a/nobr/text()')

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    text = doc.xpath('//pre')[0].text_content()
    text = text_after_line_numbers(text)
    return text

document_class = dict(
    AWS_PREFIX = 'documents/ak/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
