'''
to-do: make sure packet size is large enough to accomodate large bills
'''

import os
import re
import glob
import time
import os.path
import zipfile
import datetime
import tempfile

import MySQLdb

import scrapelib
from billy import db, settings


MYSQL_USER = getattr(settings, 'MYSQL_USER', '')
MYSQL_USER = os.environ.get('MYSQL_USER', MYSQL_USER)

MYSQL_PASSWORD = getattr(settings, 'MYSQL_PASSWORD', '')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', MYSQL_PASSWORD)

data_dir = getattr(settings, 'CA_DATA_DIR',
                   '/projects/openstates/ext/capublic/')


def get_latest():
    """
    Get and load the latest SQL dumps from the California legislature.
    """
    scraper = scrapelib.Scraper()

    meta = db.metadata.find_one({'_id': 'ca'})
    #last_update = meta['_last_update']

    base_url = "ftp://www.leginfo.ca.gov/pub/bill/"
    with scraper.urlopen(base_url) as page:

        #next_day = last_update + datetime.timedelta(days=1)
        next_day = datetime.date.today() - datetime.timedelta(weeks=1)
        next_day = datetime.datetime.combine(next_day, datetime.time())

        while next_day.date() < datetime.date.today():
            for f in parse_directory_listing(page):
                if (re.match(r'pubinfo_(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.zip',
                             f['filename'])) \
                             and f['mtime'].date() == next_day.date():

                    url = base_url + f['filename']
                    print "Getting %s" % url
                    get_and_load(url)

                    meta['_last_update'] = next_day
                    db.metadata.save(meta, safe=True)
                    break
            else:
                print "Couldn't find entry for %s" % str(next_day.date())
                break

            next_day = next_day + datetime.timedelta(days=1)


def _drop():
    '''Drop the database.'''
    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')
    cursor = connection.cursor()
    cursor.execute('DROP DATABASE capublic')
    connection.close()


def _create():
    os.chdir(data_dir)
    with open('capublic.sql') as f:
        sql = f.read()
    

    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD)
    cursor = connection.cursor()

    for sql in ["CREATE DATABASE capublic", "USE capublic", sql]:     
        cursor.execute(sql)
   
    connection.close()

    
def _startover():
    _drop()
    _create()


    

def load_data():
    '''
    Import any data files located in $CA_DATA_DIR.

    First get a list of filenames like *.dat, then for each, execute
    the corresponding .sql file after swapping out windows paths for
    $CA_DATA_DIR.
    '''
    os.chdir(data_dir)

    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')

    # For each .dat file, run its corresponding .sql file.
    for filename in glob.glob(os.path.join(data_dir, '*.dat')):

        filename = filename.replace('.dat', '.sql').lower()
        with open(os.path.join(data_dir, filename)) as f:

            # Swap out windows paths.
            script = f.read().replace(r'c:\\pubinfo\\', data_dir)
            
            cursor = connection.cursor()
            cursor.execute(script)
            #cursor.connection.commit()
            cursor.close()

    # Remove the .dat and .log filenames.
    cmd_path = os.path.dirname(__file__)
    os.system("%s %s" % (os.path.join(cmd_path, "cleanup"), data_dir))

    connection.close()

def cleanup(folder=data_dir):
    '''
    Delete all .dat and .lob files from folder.
    '''
    os.chdir(folder)
    
    # Remove the files.
    for fn in glob.glob('*.dat') + glob.glob('*.lob'):
        os.remove(fn)

    

def get_and_load(url):
    '''
    Download and extract a zipfile, then load the data.
    '''
    zip_path = download(url)
    extract(zip_path, data_dir)
    load_data()

def download(url):
    scraper = scrapelib.Scraper()
    with scraper.urlopen(url) as resp:
        (fd, path) = tempfile.mkstemp('.zip')

        with os.fdopen(fd, 'wb') as w:
            w.write(resp)

        return path


def extract(path, directory):
    z = zipfile.ZipFile(path, 'r')
    z.extractall(directory)
    z.close()


def parse_directory_listing(s):
    """
    Parse a directory listing as returned by California's legislative FTP
    server, returning entries as dictionaries with "filename", "size",
    "mtime" and "type" ('file' or 'directory') keys.
    """
    dir_re = (r'^(?P<type>[-d])[rwx-]{9,9}\s+\d+\s+\d+\s+\d+\s+'
              r'(?P<size>\d+)\s(?P<mtime>[A-Z][a-z]{2,2}\s+\d+\s+\d+:?\d*)\s+'
              r'(?P<filename>[^\n]+)$')
    dir_re = re.compile(dir_re, re.MULTILINE)

    for match in dir_re.finditer(s):
        entry = {'size': match.group('size'),
                 'filename': match.group('filename')}

        mtime = re.sub(r'\s+', ' ', match.group('mtime'))
        if ':' in mtime:
            mtime = datetime.datetime.strptime(mtime, '%b %d %H:%M')
            mtime = mtime.replace(datetime.datetime.now().year)
        else:
            mtime = datetime.datetime.strptime(mtime, '%b %d %Y').date()

        entry['mtime'] = mtime

        if match.group('type') == 'd':
            entry['type'] = 'directory'
        else:
            entry['type'] = 'file'

        yield entry


if __name__ == '__main__':
    get_latest()
