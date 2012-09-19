import lxml.html
from billy.utils.fulltext import oyster_text, text_after_line_numbers

settings = dict(SCRAPELIB_RPM=30)

metadata = dict(
    name='Pennsylvania',
    abbreviation='pa',
    capitol_timezone='America/New_York',
    legislature_name='Pennsylvania General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        dict(name='2009-2010', start_year=2009,
             end_year=2010,
             sessions=[
                 '2009-2010',
                 '2009-2010 Special Session #1 (Transportation)']),
        dict(name='2011-2012', start_year=2011,
             end_year=2012,
             sessions=[
                 '2011-2012']),
        ],
    session_details={
        '2009-2010': {'type': 'primary',
                      'display_name': '2009-2010 Regular Session',
                      '_scraped_name': '2009-2010 Regular Session',
                     },
        '2009-2010 Special Session #1 (Transportation)': {
            'type': 'special',
            'display_name': '2009-2010, 1st Special Session',
            '_scraped_name': '2009-2010 Special Session #1 (Transportation)',
        },
        '2011-2012': {'type': 'primary',
                      'display_name': '2011-2012 Regular Session',
                      '_scraped_name': '2011-2012 Regular Session',
                     },
        },
    feature_flags=['events', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '1969-1970 Regular Session',
        '1971-1972 Regular Session',
        '1971-1972 Special Session #1 ',
        '1971-1972 Special Session #2 ',
        '1973-1974 Regular Session',
        '1975-1976 Regular Session',
        '1977-1978 Regular Session',
        '1979-1980 Regular Session',
        '1981-1982 Regular Session',
        '1983-1984 Regular Session',
        '1985-1986 Regular Session',
        '1987-1988 Regular Session',
        '1987-1988 Special Session #1 ',
        '1989-1990 Regular Session',
        '1991-1992 Regular Session',
        '1991-1992 Special Session #1 ',
        '1993-1994 Regular Session',
        '1995-1996 Regular Session',
        '1995-1996 Special Session #1 ',
        '1995-1996 Special Session #2 ',
        '1997-1998 Regular Session',
        '1999-2000 Regular Session',
        '2001-2002 Regular Session',
        '2001-2002 Special Session #1 ',
        '2003-2004 Regular Session',
        '2005-2006 Regular Session',
        '2005-2006 Special Session #1 (taxpayer relief act)',
        '2007-2008 Regular Session',
        '2007-2008 Special Session #1 (Energy Policy)',
    ]
)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.state.pa.us/cfdocs/legis/home/bills/',
                     '//select[@id="billSessions"]/option/text()')

@oyster_text
def extract_text(oyster_doc, data):
    if oyster_doc['metadata']['mimetype'] in (None, 'text/html'):
        doc = lxml.html.fromstring(data)
        text = ' '.join(x.text_content() for x in doc.xpath('//tr/td[2]'))
        return text

document_class = dict(
    AWS_PREFIX = 'documents/pa/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
