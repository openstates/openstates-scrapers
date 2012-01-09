import datetime

metadata = dict(
    name='South Carolina',
    abbreviation='sc',
    legislature_name='South Carolina Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '119',
         'sessions': ['119'],
         'start_year': 2010, 'end_year': 2012},
        ],
    session_details={
        '119': {'start_date': datetime.date(2010,11,17), 'type': 'primary',
                '_scraped_name': '119 - (2011-2012)',
               },
    },
    feature_flags=[],
    _ignored_scraped_sessions=['118 - (2009-2010)', '117 - (2007-2008)',
                               '116 - (2005-2006)', '115 - (2003-2004)',
                               '114 - (2001-2002)', '113 - (1999-2000)',
                               '112 - (1997-1998)', '111 - (1995-1996)',
                               '110 - (1993-1994)', '109 - (1991-1992)',
                               '108 - (1989-1990)', '107 - (1987-1988)',
                               '106 - (1985-1986)', '105 - (1983-1984)',
                               '104 - (1981-1982)', '103 - (1979-1980)',
                               '102 - (1977-1978)', '101 - (1975-1976)']

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath( 'http://www.scstatehouse.gov/billsearch.php',
        "//select[@id='session']/option/text()" )
