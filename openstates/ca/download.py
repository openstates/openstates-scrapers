'''
This file defines functions for importing the CA database dumps in mysql.
It's set up as a fabfile, so usage is:

fab -fdownload.py db_drop
fab -fdownload.py db_create
fab -fdownload.py db_update
fab -fdownload.py download

or simply:

python download.py # runs update()


The workflow is:
 - First, wget -m the contents of the the capublic ftp directory.
 - Inspect the wget output with regex and determine which files have
   been updated, if any.
 - For each such file, unzip it in the DOWNLOADS folder.
 - For each such unzipped folder, call the import function.
 - If the folder is a sesion folder (i.e., 2011.zip, etc.), delete all 
   records pertaining to that session before importing the new data.
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

import MySQLdb, _mysql_exceptions

import scrapelib
from billy import db, settings

from fabric.api import task


MYSQL_USER = getattr(settings, 'MYSQL_USER', '')
MYSQL_USER = os.environ.get('MYSQL_USER', MYSQL_USER)

MYSQL_PASSWORD = getattr(settings, 'MYSQL_PASSWORD', '')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', MYSQL_PASSWORD)

PROJECT = settings.PROJECT_DIR
DATA = settings.DATA_DIR
DOWNLOADS = join(DATA, 'ca', 'downloads')
DBADMIN = join(DATA, 'ca', 'dbadmin')

@task
def setup():
    try:
        os.makedirs(DOWNLOADS)
    except OSError:
        pass
    zipfile.ZipFile(join(DOWNLOADS, 'pubinfo_load.zip')).extractall(DBADMIN)
    

# ----------------------------------------------------------------------------
# Logging config
#logger = logging.getLogger('billy')
logger = logging.getLogger('mysql-update')
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s', 
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)



# ---------------------------------------------------------------------------
# Miscellaneous db admin commands.

@task
def db_drop():
    '''Drop the database.'''
    logger.info('dropping capublic...')

    try:
        connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                     db='capublic')
    except _mysql_exceptions.OperationalError:
        # The database doesn't exist.
        logger.info('...no such database. Bailing.')
        return
                                            
    connection.autocommit(True)
    cursor = connection.cursor()


    cursor.execute('DROP DATABASE IF EXISTS capublic;')


    connection.close()
    logger.info('...done.')


@task
def db_create():
    '''Create the database'''

    logger.info('Creating capublic...')
    os.chdir(DBADMIN)
    
    with open('capublic.sql') as f:
        # Note: apparelty MySQLdb can't execute compound SQL statements,
        # so we have to split them up.
        sql_statements = f.read().split(';')
    
    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD)
    connection.autocommit(True)
    cursor = connection.cursor()

    # MySQL warns in OCD fashion when executing statements relating to
    # a table that doesn't exist yet. Shush, mysql...
    import warnings
    warnings.filterwarnings('ignore', 'Unknown table.*')

    for sql in sql_statements:
        cursor.execute(sql)

    cursor.close()
    connection.close()
    logger.info('...done.')


@task    
def db_startover():
    db_drop()
    db_create()

    
# ---------------------------------------------------------------------------
# Functions for updating the data.
@task
def download():
    '''
    Update the wget mirror of ftp://www.leginfo.ca.gov/pub/bill/

    Uses wget -m with default behavior and will automatically skip over 
    any files that haven't been updated on the server since the file's 
    current timestamp.
    '''
    logger.info('Updating files from ftp://www.leginfo.ca.gov/pub/bill/ ...')


    # For short: wget -m -l1 -nd -A.zip ftp://www.leginfo.ca.gov/pub/bill/
    command = ["wget",
               '--mirror',
               '--level=1',
               '--no-directories',
               '--accept=.zip', 
               '--directory-prefix=' + DOWNLOADS, 
               'ftp://www.leginfo.ca.gov/pub/bill/']

    # wget the ftp directory, and display wget output and also log to file.
    output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    updated_files = re.findall(r"([^/]+?\.zip)' saved \[\d+\]", output)
    
    if updated_files:
        msg = '...Done. Found %d updated files: %r'
        msg = msg % (len(updated_files), updated_files)
    else:
        msg = '...Done. Found no updated files.'
    logger.info(msg)
                
    return updated_files


@task
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
        logger.info(msg)
        
        zp.extractall(folder)
        folder_names.append(folder)
        
    logger.info('done extracting zipfiles.')
    return folder_names


@task
def load(folder, sql_name=partial(re.compile(r'\.dat$').sub, '.sql')):
    '''
    Import into mysql any .dat files located in `folder`.

    First get a list of filenames like *.dat, then for each, execute
    the corresponding .sql file after swapping out windows paths for
    `folder`.

    This function doesn't bother to delete the imported data files 
    afterwards; they'll be overwritten within a week, and leaving them 
    around makes testing easier (they're huge).
    '''
    logger.info('Loading data from %s...' % folder)
    
    folder = join(DOWNLOADS, folder)
    os.chdir(folder)


    connection = MySQLdb.connect(user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic')
    connection.autocommit(True)


    # For each .dat folder, run its corresponding .sql file.
    filenames = glob.glob(join(folder, '*.dat'))
    if filenames:
        logger.info('Running sql files:')

    for filename in filenames:

        # The corresponding sql file is in data/ca/dbadmin
        _, filename = split(filename)
        sql_filename = join(DBADMIN, sql_name(filename).lower())
        with open(sql_filename) as f:

            # Swap out windows paths.
            script = f.read().replace(r'c:\\pubinfo\\', folder)

        _, sql_filename = split(sql_filename)
        logger.info('...' + sql_filename)
        cursor = connection.cursor()
        cursor.execute(script)
        cursor.close()

    connection.close()
    logging.info('...Done loading from %s' % folder)


@task
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
    connection.autocommit(True)                        
    cursor = connection.cursor()
        
    for token, names in tables.items():
        for table_name in names:
            sql = ("DELETE FROM capublic.{table_name} "
                   "where {token} like '{session_year}%';")
            sql = sql.format(**locals())
            logger.debug('executing sql: "%s"' % sql)
            cursor.execute(sql)


    cursor.close()
    connection.close()
    logger.info('...done deleting session data.')


@task
def update(zipfile_names=None, unzip=True):
    '''
    If a file named `pubinfo_(?P<session_year>\d{4}).zip` has been 
    updated, delete all records in the database session_year indicated 
    in the file's name, then load the data from the zip file.

    Otherwise, load each the data from each updated `{weekday}.zip` 
    file in weekday order.

    Optionally, pass the names of one or more zipfiles as fabric kwargs
    and import those instead, i.e.:

    fab -fdownload.py update:zipfile_names=zipfile1.zip,zipfile2.zip
    '''
    logger.info('Updating capublic...')
    days='Mon Tue Wed Thu Fri Sat Sun'.split()

    # Make sure the sql scripts are unzipped in DBADMIN. 
    setup()

    if zipfile_names is None:
        
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


@task
def bootstrap(unzipped=True, zipped=True):
    '''
    Drop then create the database and load all zipfiles in DOWNLOADS. If those
    files are already unzipped, skip unzipping them.
    '''
    db_startover()

    files = glob.glob(join(DOWNLOADS, '*.zip'))

    is_unzipped = lambda fn: os.path.isdir(fn.replace('.zip', ''))
    unzipped = filter(is_unzipped, files)
    zipped = set(files) - set(unzipped)

    if unzipped:
        update(unzipped, unzip=False)

    if zipped:
        update(zipped)

@task
def add2011():
    db_startover()
    update(('pubinfo_2011.zip pubinfo_Mon.zip pubinfo_Tue.zip pubinfo_Wed.zip '
            'pubinfo_Thu.zip pubinfo_Fri.zip').split(), unzip=False)

@task
def pdb():
    pdb.set_trace()

if __name__ == '__main__':

    update()
