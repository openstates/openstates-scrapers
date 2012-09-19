import datetime
from billy.utils.fulltext import oyster_text
import lxml.html

metadata = dict(
    name='Indiana',
    abbreviation='in',
    capitol_timezone='America/New_York',
    legislature_name='Indiana General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012', 'start_year': 2011,
         'end_year': 2012, 'sessions': ['2011', '2012']},
        ],
    session_details={
        '2011': {'start_date': datetime.date(2011, 1, 5),
                 'display_name': '2011 Regular Session',
                 '_scraped_name': '2011 Regular Session',
                },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012 Regular Session',},
        },
    feature_flags=['subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/in/floor1.gif'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/in/floor2.gif'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/in/floor3.gif'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/in/floor4.gif'
        },
    ],
    _ignored_scraped_sessions=[
        '2010 Regular Session',
        '2009 Special Session',
        '2009 Regular Session',
        '2008 Regular Session',
        '2007 Regular Session',
        '2006 Regular Session',
        '2005 Regular Session',
        '2004 Regular Session',
        '2003 Regular Session',
        '2002 Special Session',
        '2002 Regular Session',
        '2001 Regular Session',
        '2000 Regular Session',
        '1999 Regular Session',
        '1998 Regular Session',
        '1997 Regular Session']
)

def session_list():
    from billy.scrape.utils import url_xpath
    # cool URL bro
    return url_xpath('http://www.in.gov/legislative/2414.htm', '//h3/text()')

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    return ' '.join(x.text_content()
                    for x in doc.xpath('//div[@align="full"]'))

document_class = dict(
    AWS_PREFIX = 'documents/in/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
