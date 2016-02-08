from billy.utils.fulltext import worddata_to_text
from .bills import OKBillScraper
from .legislators import OKLegislatorScraper
from .committees import OKCommitteeScraper
from .events import OKEventScraper

settings = dict(SCRAPELIB_TIMEOUT=120)

metadata = dict(
    name='Oklahoma',
    abbreviation='ok',
    legislature_name='Oklahoma Legislature',
    legislature_url='http://www.oklegislature.gov/',
    capitol_timezone='America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2011-2012',
         'start_year': 2011,
         'end_year': 2012,
         'sessions': ['2011-2012', '2012SS1']},
         {'name': '2013-2014',
          'start_year': 2013,
          'end_year': 2014,
          'sessions': ['2013-2014', '2013SS1']},
         {'name': '2015-2016',
          'start_year': 2015,
          'end_year': 2016,
          'sessions': ['2015-2016']},
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
        '2013SS1':
            {'display_name': '2013 Special Session',
             'session_id': '131X',
             '_scraped_name': '2013 Special Session',
            },
         '2013-2014':
            {'display_name': '2013-2014 Regular Session',
             'session_id': '1400',
             '_scraped_name': '2014 Regular Session',
            },
         '2015-2016':
            {'display_name': '2015-2016 Regular Session',
             'session_id': '1600',
             '_scraped_name': '2016 Regular Session',
            },
        },
    feature_flags=['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=[
        '2015 Regular Session',
        '2013 Regular Session',
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


def extract_text(doc, data):
    return worddata_to_text(data)
