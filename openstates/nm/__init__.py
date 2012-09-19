import lxml.html
from billy.utils.fulltext import oyster_text

metadata = {
    'abbreviation': 'nm',
    'name': 'New Mexico',
    'legislature_name': 'New Mexico Legislature',
    'capitol_timezone': 'America/Denver',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 4,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '2011-2012',
         'sessions': ['2011', '2011S', '2012'],
         'start_year': 2011, 'end_year': 2012,
        }
    ],
    'session_details': {
        '2011': {'display_name': '2011 Regular Session',
                 'slug': '11%20Regular',
                 '_scraped_name': '2011 Regular',
                },
        '2011S': {'display_name': '2011 Special Session',
                  'slug': '11%20Special',
                  '_scraped_name': '2011 1st Special',
                 },
        '2012': {'display_name': '2012 Regular Session',
                 'slug': '12%20Regular',
                 '_scraped_name': '2012 Regular',
                },
    },
    'feature_flags': ['subjects', 'influenceexplorer'],
    '_ignored_scraped_sessions': ['2010 2nd Special', '2010 Regular',
                                  '2009 1st Special', '2009 Regular',
                                  '2008 2nd Special', '2008 Regular',
                                  '2007 1st Special', '2007 Regular',
                                  '2006 Regular', '2005 1st Special',
                                  '2005 Regular', '2004 Regular',
                                  '2003 1st Special', '2003 Regular',
                                  '2002 Extraordinary', '2002 Regular',
                                  '2001 2nd Special', '2001 1st Special',
                                  '2001 Regular', '2000 2nd Special',
                                  '2000 Regular', '1999 1st Special',
                                  '1999 Regular', '1998 1st Special',
                                  '1998 Regular', '1997 Regular',
                                  '1996 1st Special', '1996 Regular']
}

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.nmlegis.gov/lcs/BillFinderNumber.aspx',
        "//select[@name='ctl00$mainCopy$SessionList']/option/text()" )

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    return doc.xpath('//body')[0].text_content().split(
        u'\r\n\xa0\r\n\xa0\r\n\xa0')[-1]

document_class = dict(
    AWS_PREFIX = 'documents/nm/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
