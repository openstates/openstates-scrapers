from billy.fulltext import (oyster_text, pdfdata_to_text,
                            text_after_line_numbers)

settings = dict(SCRAPELIB_TIMEOUT=300)

metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
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
    feature_flags=['subjects'],
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
    if oyster_doc['metadata']['mimetype'] == 'text/pdf':
        return text_after_line_numbers(pdfdata_to_text(data))

document_class = dict(
    AWS_PREFIX = 'documents/hi/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = []
)
