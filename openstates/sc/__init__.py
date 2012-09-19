import lxml.html
import datetime
from billy.utils.fulltext import oyster_text

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='South Carolina',
    abbreviation='sc',
    capitol_timezone='America/New_York',
    legislature_name='South Carolina Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '119',
         'sessions': ['119'],
         'start_year': 2010, 'end_year': 2012},
        ],
    session_details={
        '119': {'start_date': datetime.date(2010, 11, 17), 'type': 'primary',
                '_scraped_name': '119 - (2011-2012)',
                'display_name': '2011-2012 Regular Session'
               },
    },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['118 - (2009-2010)', '117 - (2007-2008)',
                               '116 - (2005-2006)', '115 - (2003-2004)',
                               '114 - (2001-2002)', '113 - (1999-2000)',
                               '112 - (1997-1998)', '111 - (1995-1996)',
                               '110 - (1993-1994)', '109 - (1991-1992)',
                               '108 - (1989-1990)', '107 - (1987-1988)',
                               '106 - (1985-1986)', '105 - (1983-1984)',
                               '104 - (1981-1982)', '103 - (1979-1980)',
                               '102 - (1977-1978)', '101 - (1975-1976)']

)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.scstatehouse.gov/billsearch.php',
        "//select[@id='session']/option/text()" )

@oyster_text
def extract_text(oyster_doc, data):
    doc = lxml.html.fromstring(data)
    # trim first and last part
    text = ' '.join(p.text_content() for p in doc.xpath('//p')[1:-1])
    return text

document_class = dict(
    AWS_PREFIX = 'documents/sc/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
