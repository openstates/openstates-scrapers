import re
import datetime

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

