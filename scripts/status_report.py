#!/usr/bin/env python
import glob
import ConfigParser
import sys, time
from optparse import make_option, OptionParser
from git import Repo

attributes = {
    'start_year':'getint',
    'bills': 'getboolean',
    'bill_versions': 'getboolean',
    'sponsors': 'getboolean',
    'actions': 'getboolean',
    'votes': 'getboolean',
    'contributors': 'get',
    'contact': 'get',
    'executable': 'get',
    'notes': 'get'}
attr_names = ('bills', 'bill_versions', 'sponsors', 'actions',
              'votes', 'start_year', 'contributors', 'contact',
              'executable', 'notes', 'authors', 'latest_commit',
             'num_commits')

verbose = True

# Output debugging information to standard error if verbose mode is enabled.
def log(msg):
    global verbose
    if verbose:
        if isinstance(msg, unicode):
            msg = msg.encode('utf-8')
        print >> sys.stderr, "LOG: " + msg

def get_state_data():
    all_files = glob.glob('./[a-z][a-z]/STATUS')
    config = ConfigParser.ConfigParser()
    config.read(all_files)
    states = config.sections()
    state_data = {}

    def parse_state(state):
        data = {}
        for key, func in attributes.iteritems():
            if config.has_option(state, key):
                try:
                    data[key] = getattr(config, func)(state, key)
                except:
                    log("Problem reading config for %s" %(state))
            else:
                data[key] = ''

        data.update(check_state_commits(config.get(state, 'abbreviation')))
        return data

    for state in sorted(states):
        yield (state, parse_state(state))

def check_state_commits(state):
    repo = Repo('..')
    data = {}
    commits = repo.commits(path='scripts/'+state, max_count=1000)
    if commits:
        data['num_commits'] = len(commits)
        data['latest_commit'] = time.strftime('%Y-%m-%d', commits[0].committed_date)
        authors = set()
        for c in commits:
            authors.add(c.author.name)
        data['authors'] = ', '.join(authors)
    return data

def html_str(val):
    if isinstance(val, bool):
        return '<div style="background-color: %s;">%s</div>' % (
            'green' if val else 'red', 'yes' if val else 'no')
    else:
        return str(val)

def build_html_table():
    option_list = (
        make_option('-v', '--verbose', action='store_true', dest='verbose',
                    default=False, help="be verbose"),
    )
    options, spares = OptionParser(
        option_list=option_list).parse_args()
    global verbose
    verbose = options.verbose

    print '<table>'
    print '<tr><th>state</th><th>%s</th></tr>' % '</th><th>'.join(attr_names)
    for state, data in get_state_data():
        log("Now looking at config for %s" % state)
        try:
            data_str = '</td><td>'.join([html_str(data[attr]) for attr in attr_names])
            print '<tr><th>%s</th><td>%s</td></tr>' % (state, data_str)
        except:
            log("missing field %s from state %s" % (attr,state))
    print '</table>'

if __name__ == '__main__':
    build_html_table()

