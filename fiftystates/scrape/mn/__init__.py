
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
         'sessions': ['2011-2012'],
         'start_year': 2011,
         'end_year': 2012,
         'biennium': '87',
        },
    ],
    session_details={
        '2009-2010': {'site_id': '0862009', 'type':'primary',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls86.asp'},
        '2010 1st Special Session': {'site_id': '1862010', 'type':'special',
             'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls8620101.asp'},
        '2010 2nd Special Session': {'site_id': '2862010', 'type':'special'},
        '2011-2012': {'site_id': '0872011', 'type':'primary',
            'votes_url': 'http://www.house.leg.state.mn.us/votes/getVotesls87.asp'},
    }
)
