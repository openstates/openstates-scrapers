import re
import datetime
from billy.utils.fulltext import pdfdata_to_text, oyster_text

metadata = dict(
    name='Nebraska',
    abbreviation='ne',
    legislature_name='Nebraska Legislature',
    capitol_timezone='America/Chicago',
#   lower_chamber_name='n/a',
    upper_chamber_name='The Unicameral',
#   lower_chamber_title='n/a',
    upper_chamber_title='Senator',
#   lower_chamber_term=2,
    upper_chamber_term=2,
    terms=[
        {'name': '2011-2012', 'sessions': ['102', '102S1'],
        'start_year': 2011, 'end_year': 2012},
    ],
    session_details={
        '102': {
            'start_date': datetime.date(2011, 1, 5),
            'end_date': datetime.date(2012, 4, 18),
            'display_name': '102nd Legislature',
            '_scraped_name': '102nd Legislature 1st and Second Sessions',
               },
        '102S1': {
            'display_name': '102nd Legislature, 1st Special Session',
            '_scraped_name': '102nd Legislature 1st Special Session',
            'start_date': datetime.date(2011, 11, 1),
            'end_date': datetime.date(2011, 11, 22)
                 }
        },
    feature_flags=['influenceexplorer'],
    _ignored_scraped_sessions=['101st Legislature 1st and Second Sessions',
                               '101st Legislature 1st Special Session',
                               '100th Legislature 1st and 2nd Sessions',
                               '100th Leg. First Special Session',
                              ]

)

def session_list():
    from billy.scrape.utils import url_xpath
    return url_xpath('http://nebraskalegislature.gov/bills/',
                     "//select[@name='Legislature']/option/text()")[:-1]

@oyster_text
def extract_text(oyster_doc, data):
    text = pdfdata_to_text(data)
    lines = text.splitlines()
    line_num_re = re.compile('\s*-\d+-')  # number:  -#-
    for i, line in enumerate(lines):
        if 'LEGISLATIVE RESOLUTION' in line:
            break
    text = ' '.join(line for line in lines[i:]
                    if not line_num_re.match(line))
    return text

document_class = dict(
    AWS_PREFIX = 'documents/ne/',
    update_mins = None,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
