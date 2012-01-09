metadata = dict(
    name='Oregon',
    abbreviation='or',
    legislature_name='Oregon Legislative Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '2011 Regular Session': {
            'display_name': '2011 Regular Session',
            '_scraped_name': '2011 Regular Session (February 1 - June 30)',
            'slug': '11reg',
        },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['2010 Special Session (February 1 - February 25)',
                               '2009 Regular Session (January 12 - June 29)',
                               '2008 Special Session (February 4 - February 22)',
                               '2007 Regular Session (January 8 - June 28)',
                               '2006 Special Session (April 20)',
                               '2005 Regular Session (January 10 - August 5)',
                               '2003 Regular Session (January 13- August 27)',
                               '2002 Special Sessions ',
                               '2001 Regular Session (January 8 - July 7)',
                               ' 1999 Regular Session (January 11 - July 24)',
                               '1997 Regular Session (January 13 - July 5)',
                               '1996 Special Session (February 1-2)',
                               '1995 Special Session (July 28 - August 2)',
                               '1995 Regular Session (January 9 - June 10)']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.leg.state.or.us/bills_laws/billsinfo.htm',
                     '//a[contains(@href, "measures")]/text()')
