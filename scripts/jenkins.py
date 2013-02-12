import os
import tempfile
import logging
import subprocess
import urllib

from zipfile import ZipFile, BadZipfile
from os.path import split, join
from urllib2 import urlopen, Request, HTTPError

from billy.core import settings


states = {
    #'aa': 'Armed Forces Americas',
    #'ae': 'Armed Forces Middle East',
    'ak': 'Alaska',
    'al': 'Alabama',
    #'ap': 'Armed Forces Pacific',
    'ar': 'Arkansas',
    #'as': 'American Samoa',
    'az': 'Arizona',
    'ca': 'California',
    'co': 'Colorado',
    'ct': 'Connecticut',
    'dc': 'District of Columbia',
    'de': 'Delaware',
    'fl': 'Florida',
    #'fm': 'Federated States of Micronesia',
    'ga': 'Georgia',
    #'gu': 'Guam',
    'hi': 'Hawaii',
    'ia': 'Iowa',
    'id': 'Idaho',
    'il': 'Illinois',
    'in': 'Indiana',
    'ks': 'Kansas',
    'ky': 'Kentucky',
    'la': 'Louisiana',
    'ma': 'Massachusetts',
    'md': 'Maryland',
    'me': 'Maine',
    #'mh': 'Marshall Islands',
    'mi': 'Michigan',
    'mn': 'Minnesota',
    'mo': 'Missouri',
    #'mp': 'Northern Mariana Islands',
    'ms': 'Mississippi',
    'mt': 'Montana',
    'nc': 'North Carolina',
    'nd': 'North Dakota',
    'ne': 'Nebraska',
    'nh': 'New Hampshire',
    'nj': 'New Jersey',
    'nm': 'New Mexico',
    'nv': 'Nevada',
    'ny': 'New York',
    'oh': 'Ohio',
    'ok': 'Oklahoma',
    'or': 'Oregon',
    'pa': 'Pennsylvania',
    'pr': 'Puerto Rico',
    #'pw': 'Palau',
    'ri': 'Rhode Island',
    'sc': 'South Carolina',
    'sd': 'South Dakota',
    'tn': 'Tennessee',
    'tx': 'Texas',
    'ut': 'Utah',
    'va': 'Virginia',
    'vi': 'Virgin Islands',
    'vt': 'Vermont',
    'wa': 'Washington',
    'wi': 'Wisconsin',
    'wv': 'West Virginia',
    'wy': 'Wyoming'}

urls = {'data': ('http://jenkins.openstates.org/job/'
                 '{state}/ws/data/{abbr}/*zip*/in.zip'),
        'cache': ('http://jenkins.openstates.org/job/'
                 '{state}/ws/cache/*zip*/cache.zip')}

# Logging config
logger = logging.getLogger('billy.janky-import')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


def _import(abbr, folder):

    # Where to put the files.
    path = split(settings.SCRAPER_PATHS[0])[0]
    path = join(path, folder)

    # Get credentials.
    # auth_header = _get_credentials()

    # Get the data.
    abbr = abbr.lower()
    state = urllib.quote(states.get(abbr))
    zip_url = urls[folder].format(**locals())
    msg = 'requesting {folder} folder for {state}...'
    logger.info(msg.format(**locals()))
    req = Request(zip_url)

    # Save it.
    f = tempfile.NamedTemporaryFile(delete=False)
    try:
        resp = urlopen(req)
    except HTTPError:
        logger.warn('Could\'t fetch from url: %s' % zip_url)
        return

    # Download huge files in chunks to avoid memory error.
    # Thanks @paultag for the tip.
    size = 4096
    read = resp.read
    chunk = read(4096)
    while chunk:
        f.write(chunk)
        chunk = read(4096)
        size += 4096

    logger.info('response ok [%d bytes]. Unzipping files...' % size)

    # Unzip this loaf.
    try:
        os.makedirs(path)
    except OSError:
        pass
    f.seek(0)
    try:
        zipfile = ZipFile(f)
    except BadZipfile:
        logger.warn('%s response wasn\'t a zip file. Skipping.' % state)
        return

    file_count = len(zipfile.namelist())
    zipfile.extractall(path)
    logger.info('Extracted %d files to %s.' % (file_count, path))

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Download data and cache files from Jenkins.')

    # Options.
    parser.add_argument('states', help='states to download data for',
                        nargs='+')

    parser.add_argument('--cache', dest='cache', action='store_const',
                       default=False, const='cache',
                       help='Download latest cache build for a state.')
    parser.add_argument('--data', dest='data', action='store_const',
                        default=True, const='data',
                        help='Download latest data build for a state.')
    parser.add_argument('--both', dest='both', action='store_true',
                        default=False,
                        help='Download latest cache, data for a state.')
    parser.add_argument('--alldata', dest='alldata', action='store_true',
                        default=False,
                        help='Download data/cache/both for all states.'),
    parser.add_argument('--import', dest='imp', action='store_true',
                        default=True,
                        help='Run import after downloading data.')

    args = parser.parse_args()

    folders = set()
    for f in ['data', 'cache']:
        if getattr(args, f):
            folders.add(f)

    if args.both:
        folders |= set(['data', 'cache'])

    _states = args.states
    if 'all' in args.states:
        _states = states

    for state in _states:
        for f in folders:
            _import(state, f)

        if args.imp:
            c = 'billy-update %s --import --report' % state
            subprocess.call(c, shell=True)
