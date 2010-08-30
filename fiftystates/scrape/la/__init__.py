import re
import urllib2
import datetime

from BeautifulSoup import BeautifulSoup


def flatten(tree):
    if tree.string:
        s = tree.string
    else:
        s = map(lambda x: flatten(x), tree.contents)
        if len(s) == 1:
            s = s[0]
    return s

internal_sessions = {}
terms = []
metadata_url = "http://www.legis.state.la.us/session.htm"

session_page = urllib2.urlopen(metadata_url)
session_page = BeautifulSoup(session_page)
for session in session_page.findAll('a'):
    if session.strong == None:
        continue
    tmp = re.split(r'\s*', ''.join(flatten(session.strong)))
    text = ' '.join(map(lambda x: x.strip(), tmp))
    year = int(re.findall(r'^[0-9]+', text)[0])
    if not year in internal_sessions:
        internal_sessions[year] = []
        terms.append({'name': str(year), 'start_year': year,
                      'end_year': year, 'sessions': [str(year)]})

    if text.endswith('Regular Legislative Session'):
        text = str(year)
    else:
        for t in terms:
            if t['start_year'] == year:
                t['sessions'].append(text)
                break

    internal_sessions[year].append((session['href'], text))

metadata = {
    'name': 'Louisiana',
    'abbreviation': 'la',
    'legislature_name': 'Louisiana Legislature',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_name': 'Senate',
    'lower_chamber_title': 'Representative',
    'upper_chamber_title': 'Senator',
    'lower_chamber_term': 4,
    'upper_chamber_term': 4,
    'terms': list(reversed(terms)),
    'session_details': {
        '2009': {'start_date': datetime.date(2010, 4, 27),
                 'end_date': datetime.date(2010, 6, 24)},
        '2010': {'start_date': datetime.date(2010, 3, 29),
                 'end_date': datetime.date(2010, 6, 21)}}}
