import re
import urllib2
import lxml.html

_year_re = re.compile(r'[1-2][0-9]{3}')
_data = urllib2.urlopen('http://www.legis.state.wi.us/').read()
_doc = lxml.html.fromstring(_data)

internal_sessions = {}
sessions = []
session_details = {}

for option in _doc.xpath("//select[@id='session']/option"):
    year = _year_re.findall(option.text)[0]
    if not year in internal_sessions:
        internal_sessions[int(year)] = []
        session_details[year] = {'years': [year], 'sub_sessions':[] }
        sessions.append(year)
    session_details[year]['sub_sessions'].append(option.text)
    internal_sessions[int(year)].append([option.values()[0], option.text])

metadata = {
    'state_name': 'Wisconsin',
    'legislature_name': 'Wisconsin State Legislature',
    'lower_chamber_name': 'Assembly',
    'upper_chamber_name': 'Senate',
    'lower_title': 'Representative',
    'upper_title': 'Senator',
    'lower_term': 2,
    'upper_term': 4,
    'sessions': sessions,
    'session_details': session_details
}
