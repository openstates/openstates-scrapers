import datetime

metadata = dict(
    _partial_vote_bill_id=True,

    name='Rhode Island',
    abbreviation='ri',
    legislature_name='Rhode Island General Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    terms=[{'name': '2012',
            'start_year': 2012,
            'start_date': datetime.date(2012, 1, 4),
            'end_year': 2012,
            'sessions': ['2012']},
          ],
    feature_flags=[],
    session_details={'2012': {'start_date': datetime.date(2012, 1, 4),
                              'type': 'primary'},
                    },
    _ignored_scraped_sessions = ['2012', '2011', '2010', '2009', '2008', '2007']
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://status.rilin.state.ri.us/bill_history.aspx?mode=previous',
                     "//select[@name='ctl00$rilinContent$cbYear']/option/text()" )
