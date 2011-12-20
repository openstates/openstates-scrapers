import datetime

metadata = dict(
    name = 'North Dakota',
    abbreviation = 'nd',
    legislature_name = 'North Dakota Legislative Assembly',
    upper_chamber_name = 'Senate',
    lower_chamber_name  = 'House of Representatives',
    upper_chamber_title = 'Senator',
    lower_chamber_title = 'Representative',
    upper_chamber_term = 4,
    lower_chamber_term = 4,
    terms = [
        {'name': '62', 'sessions': ['62'],
         'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '62' : {'start_date' : datetime.date(2011, 1, 4),
        'display_name' : '62nd Legislative Assembly',}
    },
    feature_flags=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://www.legis.nd.gov/assembly/',
        "//div[@class='linkblockassembly']/div/span/a/text()")
