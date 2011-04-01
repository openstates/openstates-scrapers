import re
import datetime
import collections

Listing = collections.namedtuple('Listing', 'mtime size filename')

def parse_directory_listing(text):
    files = []

    for match in re.finditer(r'^(\d\d-\d\d-\d\d\s+\d\d:\d\d(AM|PM))\s+(\d+)\s+(.*\.htm)\s+$', text, re.MULTILINE):
        mtime = datetime.datetime.strptime(match.group(1),
                                           "%m-%d-%y %I:%M%p")
        files.append(Listing(mtime=mtime, size=int(match.group(3)),
                             filename=match.group(4)))

    return files
