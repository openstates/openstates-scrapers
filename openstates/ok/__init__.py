from billy.utils.fulltext import oyster_text, worddata_to_text

settings = dict(SCRAPELIB_TIMEOUT=120)

metadata = dict(
    name='Oklahoma',
    abbreviation='ok',
    legislature_name='Oklahoma Legislature',
    capitol_timezone='America/Chicago',
    upper_chamber_name='Senate',
    lower_chamber_name='House',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'start_year': 2011,
         'end_year': 2012,
         'sessions': ['2011-2012', '2012SS1']},

         
        # {'name': '2013-2014',
        #  'start_year': 2013,
        #  'end_year': 2014,
        #  'sessions': ['2013']},
        ],
    session_details={
        # On the Oklahoma website they list 2011/2012 as separate sessions, but
        # bill numbering does not restart in even year sessions so we treat
        # them as the same session.  This means the session_id/_scraped_name
        # will change in even years and we'll need to ignore odd years
        '2011-2012':
            {'display_name': '2011-2012 Regular Session',
             'session_id': '1200',
             '_scraped_name': '2012 Regular Session'
            },
        '2012SS1':
            {'display_name': '2012 Special Session',
             'session_id': '121X',
             '_scraped_name': '2012 Special Session'
            },
        # '2013':
        #     {'display_name': '2013 Regular Session',
        #      'session_id': '1300',
        #      '_scraped_name': '2013 Regular Session',
        #     },
        },
    feature_flags=['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '2011 Regular Session', '2010 Regular Session',
        '2009 Regular Session', '2008 Regular Session',
        '2007 Regular Session',
        '2006 Second Special Session',
        '2006 Regular Session',
        '2005 Special Session', '2005 Regular Session',
        '2004 Special Session', '2004 Regular Session',
        '2003 Regular Session', '2002 Regular Session',
        '2001 Special Session', '2001 Regular Session',
        '2000 Regular Session', '1999 Special Session',
        '1999 Regular Session', '1998 Regular Session',
        '1997 Regular Session', '1996 Regular Session',
        '1995 Regular Session',
        '1994 Second Special Session',
        '1994 First Special Session',
        '1994 Regular Session', '1993 Regular Session']
    )


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://webserver1.lsb.state.ok.us/WebApplication2/WebForm1.aspx',
        "//select[@name='cbxSession']/option/text()")


@oyster_text
def extract_text(oyster_doc, data):
    return worddata_to_text(data)


document_class = dict(
    AWS_PREFIX='documents/ok/',
    update_mins=None,
    extract_text=extract_text,
    onchanged=['oyster.ext.elasticsearch.ElasticSearchPush']
    )
