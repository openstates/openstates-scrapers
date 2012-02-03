metadata = {
    'name': 'Georgia',
    'abbreviation': 'ga',
    'legislature_name': 'Georgia General Assembly',
    'upper_chamber_name': 'Senate',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_title': 'Senator',
    'lower_chamber_title': 'Representative',
    'upper_chamber_term': 2,
    'lower_chamber_term': 2,
    'terms': [
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011_12', '2011_ss']}
     ],
    'session_details': {
        '2011_12': {'display_name': '2011-2012 Regular Session',
                    '_scraped_name': '2011-2012 Regular Session',
                   },
        '2011_ss': {'display_name': '2011 Special Session',
                    '_scraped_name': '2011 Special Session',
                   },
    },
    'feature_flags': [],
    '_ignored_scraped_sessions': ['2009-2010 Regular Session',
                                  '2007-2008 Regular Session',
                                  '2005 Special Session',
                                  '2005-2006 Regular Session',
                                  '2004 Special Session',
                                  '2003-2004 Regular Session',
                                  '2001 2nd Special Session',
                                  '2001 1st Special Session',
                                  '2001-2002 Regular Session']
}

def session_list():
    select_id = \
        "ctl00_SPWebPartManager1_g_3ddc9629_a44e_4724_ae40_c80247107bd6_Session"
    from billy.scrape.utils import url_xpath
    sessions = url_xpath(
        'http://www.legis.ga.gov/Legislation/en-US/Search.aspx',
        "//select")[1].xpath("option/text()")
    # XXX: If this breaks, it's because of this wonky xpath thing.
    #      the ID seemed to change when I was testing it. This works
    #      well enough for now.
    sessions = [ session.strip() for session in sessions ]
    return sessions
