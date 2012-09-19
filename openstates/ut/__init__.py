import datetime
from billy.utils.fulltext import (pdfdata_to_text, oyster_text,
                            text_after_line_numbers)

metadata = dict(
    name='Utah',
    abbreviation='ut',
    legislature_name='Utah State Legislature',
    capitol_timezone='America/Denver',
    lower_chamber_name='House',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    upper_chamber_term=4,
    terms=[
        dict(name='2011-2012', sessions=['2011', '2011S1', '2011S2', '2011S3',
                                         '2012', '2012S4'],
             start_year=2011, end_year=2012),
        ],
    session_details={
        '2011': {'start_date': datetime.date(2011, 1, 24),
                 'display_name': '2011 Regular Session',
                 '_scraped_name': '2011 General Session',
                },
        '2011S1': { 'display_name': '2011, 1st Special Session',
                    '_scraped_name': '2011 1st Special Session'},
        '2011S2': { 'display_name': '2011, 2nd Special Session',
                    '_scraped_name': '2011 2nd Special Session'},
        '2011S3': { 'display_name': '2011, 3rd Special Session',
                    '_scraped_name': '2011 3rd Special Session'},
        '2012': { 'display_name': '2012 General Session',
                  '_scraped_name': '2012 General Session', },
        '2012S4': { 'display_name': '2012, 4th Special Session',
                    '_scraped_name': '2012 4th Special Session'},
    },
    feature_flags=['events', 'subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '2010 2nd Special Session',
        '2010 General Session',
        '2009 1st Special Session',
        '2009 General Session',
        '2008 2nd Special Session',
        '2008 General Session',
        '2007 1st Special Session',
        '2007 General Session',
        '2006 5th Special Session',
        '2006 4th Special Session',
        '2006 3rd Special Session',
        '2006 General Session',
        '2005 2nd Special Session',
        '2005 1st Special Session',
        '2005 General Session',
        '2004 4th Special Session',
        '2004 3rd Special Session',
        '2004 General Session',
        '2003 2nd Special Session',
        '2003 1st Special Session',
        '2003 General Session',
        '2002 6th Special Session',
        '2002 5th Special Session',
        '2002 4th Special Session',
        '2002 3rd Special Session',
        '2002 General Session',
        '2001 2nd Special Session',
        '2001 1st Special Session',
        '2001 General Session',
        '2000 General Session',
        '1999 General Session',
        '1998 General Session',
        '1997 2nd Special Session',
        '1997 1st Special Session',
        '1997 General Session']

)

def session_list():
    from billy.scrape.utils import url_xpath
    sessions = url_xpath( 'http://le.utah.gov/',
        "//select[@name='Sess']/option/text()" )
    return [ session.strip() for session in sessions ]

@oyster_text
def extract_text(oyster_doc, data):
    if oyster_doc['metadata']['mimetype'] == 'application/pdf':
        return text_after_line_numbers(pdfdata_to_text(data))

document_class = dict(
    AWS_PREFIX = 'documents/ut/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
