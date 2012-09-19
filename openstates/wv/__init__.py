from billy.utils.fulltext import oyster_text
import lxml.html

metadata = {
    'abbreviation': 'wv',
    'capitol_timezone': 'America/New_York',
    'name': 'West Virginia',
    'legislature_name': 'West Virginia Legislature',
    'lower_chamber_name': 'House',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Delegate',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 2,
    'upper_chamber_term': 4,
    'terms': [
        {'name': '2011-2012',
         'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011','2012'],
         }
        ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 '_scraped_name': '2011'
                 },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012'
                 },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2010', '2009', '2008', '2007', '2006',
                                  '2005', '2004', '2003', '2002', '2001',
                                  '2000', '1999', '1998', '1997', '1996',
                                  '1995', '1994', '1993']

}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.wv.us/Bill_Status/Bill_Status.cfm',
                     '//select[@name="year"]/option/text()')

@oyster_text
def extract_text(oyster_doc, data):
    if (oyster_doc['metadata']['mimetype'] == 'text/html' or 
        'bills_text.cfm' in oyster_doc['url']):
        doc = lxml.html.fromstring(data)
        return '\n'.join(p.text_content() for p in
                         doc.xpath('//div[@id="bhistcontent"]/p'))

document_class = dict(
    AWS_PREFIX = 'documents/wv/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
