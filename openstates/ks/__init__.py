import datetime

# most info taken from http://www.kslib.info/constitution/art2.html
# also ballotpedia.org
metadata = dict(
    name='Kansas',
    abbreviation='ks',
    legislature_name='Kansas State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms=[
        {'name': '2011-2012',
         'sessions': ['2011-2012'],
         'start_year': 2011, 'end_year': 2012,},
    ],
    session_details={
        '2011-2012': {
            'start_date': datetime.date(2011, 1, 12),
            'display_name': '2011-2012 Regular Session',
            'type': 'primary',
            '_scraped_name': 'b2011_12',
        },
    },
    feature_flags=[],
)

def session_list():
    from billy.scrape.utils import url_xpath
    url = url_xpath('http://www.kslegislature.org/li',
                     '//a[contains(text(), "Senate Bills")]/@href')[0]
    slug = url.split('/')[2]
    return [slug]
