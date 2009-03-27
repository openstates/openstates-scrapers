#!/usr/bin/env python

import glob
import ConfigParser

attributes = {
    'start_year':'getint',
    'bills': 'getboolean',
    'bill_versions': 'getboolean',
    'sponsors': 'getboolean',
    'actions': 'getboolean',
    'votes': 'getboolean',
    'contributors': 'get',
    'notes': 'get'}
attr_names = ('bills', 'bill_versions', 'sponsors', 'actions',
              'votes', 'start_year', 'contributors', 'notes')

def get_state_data():
    all_files = glob.glob('./*/STATUS')
    config = ConfigParser.ConfigParser()
    config.read(*all_files)
    states = config.sections()
    state_data = {}

    def parse_state(state):
        data = {}
        for key, func in attributes.iteritems():
            data[key] = getattr(config, func)(state, key)
        return data

    for state in states:
        yield (state, parse_state(state))

def html_str(val):
    if isinstance(val, bool):
        return '<div style="background-color: %s;">%s</div>' % (
            'green' if val else 'red', 'yes' if val else 'no')
    else:
        return str(val)

def build_html_table():
    print '<table>'
    print '<tr><th>state</th><th>%s</th></tr>' % '</th><th>'.join(attr_names)
    for state, data in get_state_data():
        data_str = '</td><td>'.join([html_str(data[attr]) for attr in attr_names])
        print '<tr><th>%s</th><td>%s</td></tr>' % (state, data_str)
    print '</table>'

if __name__ == '__main__':
    build_html_table()
