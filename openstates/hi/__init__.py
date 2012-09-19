from billy.utils.fulltext import (oyster_text, pdfdata_to_text,
                            text_after_line_numbers)

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    capitol_timezone='Pacific/Honolulu',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        {
            'name': '2011-2012',
            'sessions': [
                '2011 Regular Session',
            ],
            'start_year' : 2011,
            'end_year'   : 2012
        },
     ],
    session_details={
        '2011 Regular Session' : {
            'display_name'  : '2011-2012 Regular Session',
            # was 2011, now 2012 to make scraper keep working for 2011-2012
            '_scraped_name' : '2012'
        },
        # name next session 2013-2014 instead of following pattern
    },
    feature_flags=['subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Chamber Floor",
         "url": 'http://static.openstates.org/capmaps/hi/floorchamber.pdf'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/hi/floor2.pdf'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/hi/floor3.pdf'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/hi/floor4.pdf'
        },
        {"name": "Floor 5",
         "url": 'http://static.openstates.org/capmaps/hi/floor5.pdf'
        },
    ],
    _ignored_scraped_sessions = [
        # ignore odd years after they're over..
        '2011',
        '2010', '2009', '2008', '2007', '2006',
        '2005', '2004', '2003', '2002', '2001',
        '2000', '1999'
    ]
)

def session_list():
    # doesn't include current session, we need to change it
    from billy.scrape.utils import url_xpath
    sessions = url_xpath('http://www.capitol.hawaii.gov/archives/main.aspx',
            "//div[@class='roundedrect gradientgray shadow']/a/text()"
        )
    sessions.remove("Archives Main")
    return sessions

@oyster_text
def extract_text(oyster_doc, data):
    if oyster_doc['metadata']['mimetype'] == 'application/pdf':
        return text_after_line_numbers(pdfdata_to_text(data))

document_class = dict(
    AWS_PREFIX = 'documents/hi/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
