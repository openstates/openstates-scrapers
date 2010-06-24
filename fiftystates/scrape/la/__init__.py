import re
import urllib2

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
sessions = []
session_details = {}
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
        sessions.append({'name': str(year), 'start_year': year,
                         'end_year': year, 'sub_sessions': []})

    if text.endswith('Regular Legislative Session'):
        text = str(year)
    else:
        for s in sessions:
            if s['start_year'] == year:
                s['sub_sessions'].append(text)
                break

    internal_sessions[year].append((session['href'], text))

metadata = {
    'name': 'Louisiana',
    'abbreviation': 'la',
    'legislature_name': 'Louisiana Legislature',
    'lower_chamber_name': 'House of Representatives',
    'upper_chamber_name': 'Senate',
    'lower_title': 'Representative',
    'upper_title': 'Senator',
    'lower_term': 4,
    'upper_term': 4,
    'sessions': list(reversed(sessions))}
