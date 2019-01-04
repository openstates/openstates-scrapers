'''
This file defines functions for importing the CA database dumps in mysql.

The workflow is:
 - Drop & recreate the local capublic database.
 - Inspect the FTP site with regex and determine which files have been updated, if any.
 - For each such file, unzip it & call import.
'''
import os
import re
import glob
import os.path
import subprocess
import logging
import lxml.html
from datetime import datetime
from os.path import join, split
from functools import partial
from collections import namedtuple

import requests
import MySQLdb
import _mysql_exceptions


MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQL_USER', 'mysql')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')

BASE_URL = 'https://downloads.leginfo.legislature.ca.gov/'


# ----------------------------------------------------------------------------
# Logging config
logger = logging.getLogger('pupa.ca-update')
# logger.setLevel(logging.INFO)

# ch = logging.StreamHandler()
# formatter = logging.Formatter('%(asctime)s - %(message)s',
#                               datefmt='%H:%M:%S')
# ch.setFormatter(formatter)
# logger.addHandler(ch)

# ---------------------------------------------------------------------------
# Miscellaneous db admin commands.


def clean_text(s):
    # replace smart quote characters
    s = re.sub(r'[\u2018\u2019]', "'", s)
    s = re.sub(r'[\u201C\u201D]', '"', s)
    s = s.replace('\xe2\u20ac\u02dc', "'")
    return s


def db_drop():
    '''Drop the database.'''
    logger.info('dropping capublic...')

    try:
        connection = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER,
                                     passwd=MYSQL_PASSWORD, db='capublic')
    except _mysql_exceptions.OperationalError:
        # The database doesn't exist.
        logger.info('...no such database. Bailing.')
        return

    connection.autocommit(True)
    cursor = connection.cursor()

    cursor.execute('DROP DATABASE IF EXISTS capublic;')

    connection.close()
    logger.info('...done.')


# ---------------------------------------------------------------------------
# Functions for updating the data.
DatRow = namedtuple(
    'DatRow',
    [
        'bill_version_id', 'bill_id', 'version_num',
        'bill_version_action_date', 'bill_version_action',
        'request_num', 'subject', 'vote_required',
        'appropriation', 'fiscal_committee', 'local_program',
        'substantive_changes', 'urgency', 'taxlevy',
        'bill_xml', 'active_flg', 'trans_uid', 'trans_update'
    ]
)


def dat_row_2_tuple(row):
    '''Convert a row in the bill_version_tbl.dat file into a
    namedtuple.
    '''
    cells = row.split('\t')
    res = []
    for cell in cells:
        if cell.startswith('`') and cell.endswith('`'):
            res.append(cell[1:-1])
        elif cell == 'NULL':
            res.append(None)
        else:
            res.append(cell)
    return DatRow(*res)


def encode_or_none(value):
    return value.encode() if value else None


def load_bill_versions(connection):
    '''
    Given a data folder, read its BILL_VERSION_TBL.dat file in python,
    construct individual REPLACE statements and execute them one at
    a time. This method is slower that letting mysql do the import,
    but doesn't fail mysteriously.
    '''

    sql = '''
        REPLACE INTO capublic.bill_version_tbl (
            BILL_VERSION_ID,
            BILL_ID,
            VERSION_NUM,
            BILL_VERSION_ACTION_DATE,
            BILL_VERSION_ACTION,
            REQUEST_NUM,
            SUBJECT,
            VOTE_REQUIRED,
            APPROPRIATION,
            FISCAL_COMMITTEE,
            LOCAL_PROGRAM,
            SUBSTANTIVE_CHANGES,
            URGENCY,
            TAXLEVY,
            BILL_XML,
            ACTIVE_FLG,
            TRANS_UID,
            TRANS_UPDATE)

        VALUES (%s)
        '''
    sql = sql % ', '.join(['%s'] * 18)

    cursor = connection.cursor()
    with open('BILL_VERSION_TBL.dat') as f:
        for row in f:
            # The files are supposedly already in utf-8, but with
            # copious bogus characters.
            row = clean_text(row)
            row = dat_row_2_tuple(row)
            with open(row.bill_xml) as f:
                text = f.read()
                text = clean_text(text)
                row = row._replace(bill_xml=text)
                cursor.execute(sql, [encode_or_none(column) for column in row])

    cursor.close()


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
    os.chdir(folder)

    connection = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD,
                                 db='capublic', local_infile=1)
    connection.autocommit(True)

    filenames = glob.glob('*.dat')

    for filename in filenames:

        # The corresponding sql file is in data/ca/dbadmin
        _, filename = split(filename)
        sql_filename = join('../pubinfo_load', sql_name(filename).lower())
        with open(sql_filename) as f:

            # Swap out windows paths.
            script = f.read().replace(r'c:\\pubinfo\\', folder)

        _, sql_filename = split(sql_filename)
        logger.info('loading ' + sql_filename)
        if sql_filename == 'bill_version_tbl.sql':
            logger.info('inserting xml files (slow)')
            load_bill_versions(connection)
        else:
            cursor = connection.cursor()
            cursor.execute(script)
            cursor.close()

    connection.close()
    os.chdir('..')
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

    connection = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD,
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


def db_create():
    '''Create the database'''

    logger.info('Creating capublic...')

    dirname = get_zip('pubinfo_load.zip')
    os.chdir(dirname)

    with open('capublic.sql') as f:
        # Note: apparently MySQLdb can't execute compound SQL statements,
        # so we have to split them up.
        sql_statements = f.read().split(';')

    connection = MySQLdb.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD)
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
    os.chdir('..')


def get_contents():
    resp = {}
    # for line in urllib.urlopen(BASE_URL).read().splitlines()[1:]:
    #     print line
    #     date, filename = re.match(
    #         '[drwx-]{10}\s+\d\s+\d{3}\s+\d{3}\s+\d+ (\w+\s+\d+\s+\d+:?\d*) (\w+.\w+)',
    #         line,
    #     ).groups()
    #     date = date.replace('  ', ' ')
    #     try:
    #         date = datetime.strptime(date, '%b %d %Y')
    #     except ValueError:
    #         date = ' '.join([date, str(datetime.now().year)])
    #         date = datetime.strptime(date, '%b %d %H:%M %Y')
    #     resp[filename] = date
    # return resp

    html = requests.get(BASE_URL).text
    doc = lxml.html.fromstring(html)
    # doc.make_links_absolute(BASE_URL)
    rows = doc.xpath('//table/tr')
    for row in rows[2:]:
        date = row.xpath('string(td[3])').strip()
        if date:
            date = datetime.strptime(date, '%d-%b-%Y %H:%M')
            filename = row.xpath('string(td[2]/a[1]/@href)')
            resp[filename] = date
    return resp


def _check_call(*args):
    logging.info('calling ' + ' '.join(args))
    subprocess.check_call(args)


def get_zip(filename):
    dirname = filename.replace('.zip', '')
    _check_call('wget', '--no-check-certificate', BASE_URL + filename)
    _check_call('rm', '-rf', dirname)
    _check_call('unzip', filename, '-d', dirname)
    _check_call('rm', '-rf', filename)
    return dirname


def get_current_year(contents):
    newest_file = '2000'
    newest_file_date = datetime(2000, 1, 1)
    files_to_get = []

    # get file for latest year
    for filename, date in contents.items():
        date_part = filename.replace('pubinfo_', '').replace('.zip', '')
        if date_part.startswith('20') and filename > newest_file:
            newest_file = filename
            newest_file_date = date
    files_to_get.append(newest_file)

    # get files for days since last update
    days = ('pubinfo_Mon.zip', 'pubinfo_Tue.zip', 'pubinfo_Wed.zip', 'pubinfo_Thu.zip',
            'pubinfo_Fri.zip', 'pubinfo_Sat.zip')
    for dayfile in days:
        if contents[dayfile] > newest_file_date:
            files_to_get.append(dayfile)

    for file in files_to_get:
        dirname = get_zip(file)
        load(dirname)


if __name__ == '__main__':
    db_drop()
    db_create()
    contents = get_contents()
    get_current_year(contents)
