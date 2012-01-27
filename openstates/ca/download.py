'''
to-do: make sure packet size is large enough to accomodate large bills
'''
import pdb
import sys
import os
import re
import glob
import time
import os.path
import zipfile
import datetime
import tempfile
import subprocess
import logging
from os.path import join, split
from functools import partial
from zipfile import ZipFile

import MySQLdb

import scrapelib
from billy import db, settings



MYSQL_USER = getattr(settings, 'MYSQL_USER', '')
MYSQL_USER = os.environ.get('MYSQL_USER', MYSQL_USER)

MYSQL_PASSWORD = getattr(settings, 'MYSQL_PASSWORD', '')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', MYSQL_PASSWORD)

PROJECT = settings.PROJECT_DIR
DATA = settings.DATA_DIR
DOWNLOADS = join(DATA, 'ca', 'downloads')
DBADMIN = join(DATA, 'ca', 'dbadmin')


def setup():
    try:
        os.makedirs(DOWNLOADS)
    except OSError:
        pass
    zipfile.ZipFile(join(DOWNLOADS, 'pubinfo_load.zip')).extractall(DBADMIN)
    

# ----------------------------------------------------------------------------
# Logging config
logger = logging.getLogger('CA[mysql-update]')
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(asctime)s - %(message)s',
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)



# ---------------------------------------------------------------------------
# Miscellaneous db admin commands.
def _drop():
    '''Drop the database.'''
    logger.info('dropping capublic...')
    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')
    cursor = connection.cursor()
    cursor.execute('DROP DATABASE capublic;')
    connection.close()
    logger.info('dropping capublic')


def _create():

    logger.info('Creating capublic...')
    os.chdir(DBADMIN)
    
    with open('capublic.sql') as f:
        sql = f.read()
    
    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD)
    cursor = connection.cursor()

    for sql in ["CREATE DATABASE capublic;", sql]:     
        cursor.execute(sql)
   
    connection.close()
    logger.info('...done creating capublic')

    
def _startover():
    _drop()
    _create()

    
# ---------------------------------------------------------------------------
# Functions for updating the data.

def download():
    '''
    Update the wget mirror of ftp://www.leginfo.ca.gov/pub/bill/

    Uses wget -m with default behavior and will automatically skip over any files
    that haven't been updated on the server since the file's current timestamp.
    '''
    logger.info('Updating files from ftp://www.leginfo.ca.gov/pub/bill/ ...')

    # For short: wget -m -l1 -nd -A.zip ftp://www.leginfo.ca.gov/pub/bill/
    command = ["wget",
               '--output-file="wget-output"',
               '--mirror',
               '--level=1',
               '--no-directories',
               '--accept=.zip', 
               '--directory-prefix=%s' % DOWNLOADS, 
               'ftp://www.leginfo.ca.gov/pub/bill/']

    # wget the ftp directory, and display wget output and also log to file.
    command = ' '.join(command) + ' && tail wget-output'
    subprocess.call(command, shell=True)

    # Figure out which files were updated.
    with open('wget-output') as f:
        output = f.read()
    updated_files = re.findall(r"([^/]+?\.zip)' saved \[\d+\]", output)

    if updated_files:
        msg = '...Done. Found %d updated files: %r'
        msg = msg % (len(updated_files), updated_files)
    else:
        msg = '...Done. Found no updated files.'
    logger.info(msg)
                
    return updated_files



def extract(zipfile_names, strip=partial(re.compile(r'\.zip$').sub, '')):
    '''
    Extract any zipfiles in our cache that have been updated.
    '''
    logger.info('Extracting zipfiles. This could take a while...')
    os.chdir(DOWNLOADS)
    folder_names = []
    for z in zipfile_names:
        folder = strip(z) + os.path.sep
        zp = ZipFile(z)

        msg = 'Extracting %d files to %s...' % (len(zp.namelist()), folder)
        logger.debug(msg)
        
        zp.extractall(folder)
        folder_names.append(folder)
        
    logger.info('done extracting zipfiles.')
    return folder_names



def load(folder, sql_name=partial(re.compile(r'\.dat$').sub, '.sql')):
    '''
    Import any data files located in `folder`.

    First get a list of filenames like *.dat, then for each, execute
    the corresponding .sql file after swapping out windows paths for
    `folder`.

    This function doesn't bother to delete the imported data files afterwards.
    They'll be overwritten within a week, and leaving them around makes testing
    easier (they're huge).
    '''
    logger.info('Loading data from %s...' % folder)
    
    folder = join(DOWNLOADS, folder)
    os.chdir(folder)

    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')

    # For each .dat folder, run its corresponding .sql file.
    for filename in glob.glob(join(folder, '*.dat')):

        # The corresponding sql file is in the data/ca/dbadmin...
        _, filename = split(filename)
        sql_filename = join(DBADMIN, sql_name(filename).lower())
        with open(sql_filename) as f:

            # Swap out windows paths.
            script = f.read().replace(r'c:\\pubinfo\\', folder)
            
            
        cursor = connection.cursor()

        _, slq_filename = split(sql_filename)
        #logger.debug('Running .sql file %s...' % sql_filename)
        cursor.execute(script)

    cursor.close()
    connection.close()
    logging.info('...Done loading from %s' % folder)


def delete_session(session_year):
    '''
    This is the python equivalent (or at least, is supposed to be)
    of the deleteSession.bat file included in the pubinfo_load.zip file.

    It deletes all the entries for the specified session.
    Used before the weekly import of the new database dump on Sunday.
    '''
    tables = {
        'bill_id': [
            'bill_detail_vote_tbl',
            'bill_history_tbl',
            'bill_summary_vote_tbl',
            'bill_analysis_tbl',
            'bill_tbl',
            'committee_hearing_tbl',
            'daily_file_tbl'
            ],
        
        'bill_version_id': [
            'bill_version_authors_tbl',
            'bill_version_tbl'
            ],

        'session_year': [
            'legislator_tbl',
            'location_code_tbl'
            ]
        }


    logger.info('Deleting all data for session year %s...' % session_year)

    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')
    cursor = connection.cursor()
        
    for token, names in tables.items():
        for table_name in names:
            sql = ("DELETE FROM capublic.{table_name} "
                   "where {token} like '{session_year}%';")
            sql = sql.format(**locals())
            logger.debug('executing sql: "%s"' % sql)
            cursor.execute(sql)
            cursor.connection.commit()

    cursor.close()
    connection.close()
    logger.info('...done deleting session data.')

    
def update(zipfile_names, unzip=True):
    '''
    If a file named `pubinfo_(?P<session_year>\d{4}).zip` has been updated, delete
    all records in the database session_year indicated in the file's name, then load
    the data from the zip file.

    Otherwise, load each the data from each updated `{weekday}.zip` file in
    weekday order.

    Optionally, pass the names of one or more zipfiles to this module
    on the command line, and it will import those instead.
    '''
    logger.info('Updating capublic...')
    days='Mon Tue Wed Thu Fri Sat Sun'.split()

    # Make sure the sql scripts are unzipped in DBADMIN. 
    setup()

    if not zipfile_names:
        
        zipfile_names = download()
        
        if not zipfile_names:
            logger.info('No updated files found; exiting.')
            sys.exit(0)

    if unzip:
        folder_names = extract(zipfile_names)
    else:
        folder_names = [x.replace('.zip', '') + '/' for x in zipfile_names]
        
        


    # ------------------------------------------------------------------------
    # Update any session updates in order.
    
    # Get a list of session folder names, usually only one, like ['pubinfo_2011']
    session_folders = filter(re.compile(r'\d{4}').search, folder_names)

    for folder in session_folders:

        # Delete all records relating to this session year.
        session_year = re.search('\d{4}', folder).group()
        delete_session(session_year)

        # Load the new data.
        load(folder)


    # ------------------------------------------------------------------------
    # Apply any daily updates in order.

    for s in session_folders:
        folder_names.remove(s)

    def sorter(foldername, re_day=re.compile(r'Mon|Tue|Wed|Thu|Fri|Sat', re.I)):
        day = re_day.search(foldername).group()
        return days.index(day)

    # Get a list of daily folder names, like ['pubinfo_Mon', 'pubinf_Tue']
    daily_folders = list(sorted(folder_names, key=sorter))

    for folder in daily_folders:
        load(folder)


def bootstrap(unzipped=True, zipped=True):
    '''
    Drop then create the database and load all zipfiles in DOWNLOADS. If those
    files are already unzipped, skip unzipping them.
    '''
    _drop()
    _create()

    files = glob.glob(join(DOWNLOADS, '*.zip'))

    is_unzipped = lambda fn: os.path.isdir(fn.replace('.zip', ''))
    unzipped = filter(is_unzipped, files)
    zipped = set(files) - set(unzipped)

    if unzipped:
        update(unzipped, unzip=False)

    if zipped:
        update(zipped)

def add2011():
    update(('pubinfo_Wed.zip '
            'pubinfo_Thu.zip pubinfo_Fri.zip').split(), unzip=False)

if __name__ == '__main__':

    import sys
    if 1 < len(sys.argv):
        if sys.argv[1] == "bootstrap":
            bootstrap()
        elif sys.argv[1] == 'add2011':
           add2011()
        else:
            update(*sys.argv[1:])
    else:
        update()
