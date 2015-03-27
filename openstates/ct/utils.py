import re
import datetime
import collections
import chardet
import unicodecsv
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


def open_csv(data):
    char_encoding = chardet.detect(data.content)['encoding']
    return unicodecsv.DictReader(StringIO.StringIO(data.content),
                                 encoding=char_encoding)


Listing = collections.namedtuple('Listing', 'mtime size filename')


def parse_directory_listing(text):
    files = []

    dir_re = r'^(\d\d-\d\d-\d\d\s+\d\d:\d\d(AM|PM))\s+(\d+)\s+(.*\.htm)\s+$'
    for match in re.finditer(dir_re, text, re.MULTILINE):
        mtime = datetime.datetime.strptime(match.group(1),
                                           "%m-%d-%y %I:%M%p")
        files.append(Listing(mtime=mtime, size=int(match.group(3)),
                             filename=match.group(4)))

    return files
