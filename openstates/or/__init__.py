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
    terms = [
        {'name': '2011-2012',
         'sessions': ['2011 Regular Session'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '2011 Regular Session': {'display_name': '2011 Regular Session'},
    },
    feature_flags=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.leg.state.or.us/bills_laws/billsinfo.htm',
        "//table[@class='stanTable']/tr/td/a/text()")
