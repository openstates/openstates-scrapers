import datetime

metadata = dict(
    name='Indiana',
    abbreviation='in',
    legislature_name='Indiana General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
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
    feature_flags=['subjects'],
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
