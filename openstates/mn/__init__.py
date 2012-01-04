
metadata = dict(
    name='Minnesota',
    abbreviation='mn',
    legislature_name='Minnesota State Legislature',
    lower_chamber_name='House of Representatives',
    upper_chamber_name='Senate',
    lower_chamber_title='Representative',
    upper_chamber_title='Senator',
    lower_chamber_term=2,
    # 4 yr terms in years ending in 2 and 6.  2 yr terms in years ending in 0
    upper_chamber_term='http://en.wikipedia.org/wiki/Minnesota_Senate',
    terms=[
        {'name': '2009-2010',
         'sessions': ['2009-2010', '2010 1st Special Session',
                      '2010 2nd Special Session'],
         'start_year': 2009,
         'end_year': 2010,
         'biennium': '86',
        },
        {'name': '2011-2012',
         'sessions': ['2011-2012', '2011s1'],
         'start_year': 2011,
         'end_year': 2012,
         'biennium': '87',
        },
    ],
    session_details={
        '2009-2010': {
            'site_id': '0862009', 'type':'primary',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls86.asp',
            'display_name': '2009-2010 Regular Session',
            '_scraped_name': '86th Legislature, 2009-2010',
        },
        '2010 1st Special Session': {
            'site_id': '1862010', 'type':'special',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls8620101.asp',
            'display_name': '2010, 1st Special Session',
            '_scraped_name': '86th Legislature, 2010 1st Special Session',
        },
        '2010 2nd Special Session': {
            'site_id': '2862010', 'type':'special',
            'display_name': '2010, 2nd Special Session',
            '_scraped_name': '86th Legislature, 2010 2nd Special Session',
        },
        '2011-2012': {
            'site_id': '0872011', 'type':'primary',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls87.asp',
            'display_name': '2011-2012 Regular Session',
            '_scraped_name': '87th Legislature, 2011-2012',
        },
        '2011s1': {
            'site_id': '1872011', 'type': 'special',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls8720111.asp',
            'display_name': '2011, 1st Special Session',
            '_scraped_name': '87th Legislature, 2011 1st Special Session',
        },
    },
    feature_flags=['subjects'],
    _ignored_scraped_sessions=['85th Legislature, 2007-2008',
                               '85th Legislature, 2007 1st Special Session',
                               '84th Legislature, 2005-2006',
                               '84th Legislature, 2005 1st Special Session',
                               '83rd Legislature, 2003-2004',
                               '83rd Legislature, 2003 1st Special Session',
                               '82nd Legislature, 2001-2002',
                               '82nd Legislature, 2002 1st Special Session',
                               '82nd Legislature, 2001 1st Special Session',
                               '81st Legislature, 1999-2000',
                               '80th Legislature, 1997-1998',
                               '80th Legislature, 1998 1st Special Session',
                               '80th Legislature, 1997 3rd Special Session',
                               '80th Legislature, 1997 2nd Special Session',
                               '80th Legislature, 1997 1st Special Session',
                               '79th Legislature, 1995-1996',
                               '79th Legislature, 1995 1st Special Session']

)


def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('https://www.revisor.mn.gov/revisor/pages/search_status/'
                     'status_search.php?body=House',
                     '//select[@name="session"]/option/text()')
