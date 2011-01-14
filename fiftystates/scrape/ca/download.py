import os
import re
import os.path
import zipfile
import datetime
import tempfile
import scrapelib

from fiftystates import settings
from fiftystates.backend import db

def get_latest():
    """
    Get and load the latest SQL dumps from the California legislature.
    """
    scraper = scrapelib.Scraper()

    meta = db.metadata.find_one({'_id': 'ca'})
    last_update = meta['_last_update']

    base_url = "ftp://www.leginfo.ca.gov/pub/bill/"
    with scraper.urlopen(base_url) as page:
        next_day = last_update + datetime.timedelta(days=1)

        while next_day.date() < datetime.date.today():
            for f in parse_directory_listing(page):
                if (re.match(r'pubinfo_(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.zip',
                             f['filename'])
                    and f['mtime'].date() == next_day.date()):

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


def get_and_load(url):
    user = os.environ.get('MYSQL_USER', getattr(settings, 'MYSQL_USER',
                                                ''))
    password = os.environ.get('MYSQL_PASSWORD', getattr(settings,
                                                        'MYSQL_PASSWORD',
                                                        ''))

    cmd_path = os.path.dirname(__file__)
    data_dir = getattr(settings, 'CA_DATA_DIR',
                       '/projects/openstates/ext/capublic/')
    zip_path = download(url)
    extract(zip_path, data_dir)

    os.system("%s localhost %s %s %s" % (os.path.join(cmd_path, "load_data"),
                                         user, password, data_dir))
    os.system("%s %s" % (os.path.join(cmd_path, "cleanup"), data_dir))

    os.remove(zip_path)

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
