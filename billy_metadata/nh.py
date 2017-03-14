import lxml
import csv

metadata = {
    'abbreviation': 'nh',
    'name': 'New Hampshire',
    'capitol_timezone': 'America/New_York',
    'legislature_name': 'New Hampshire General Court',
    'legislature_url': 'http://www.gencourt.state.nh.us/',
    'chambers': {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    'terms': [
        {'name': '2017-2018', 'sessions': ['2017'],
         'start_year': 2017, 'end_year': 2018}
    ],
    'session_details': {
        '2017': {'display_name': '2017 Regular Session',
                 '_scraped_name': '2017 Session',
                 'type': 'primary'
                },
    },
    '_ignored_scraped_sessions': [],
}

def session_list():
    # csv.register_dialect('piper', delimiter='|', quoting=csv.QUOTE_NONE)

    # # Grab the main bill list and look for unique years
    # csv = self.get('http://gencourt.state.nh.us/dynamicdatafiles/LSRs.txt')
    # csv = csv.reader(csv)
    # csv = csv.DictReader(csv, dialect='piper'):
    return ['2017']
