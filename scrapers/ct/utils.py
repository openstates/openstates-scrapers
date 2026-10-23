import re
import datetime
import collections
import csv
from io import StringIO


def open_csv(data):
    # Don't rely on chardet here: it only samples the first 200KB by default,
    # and CT's bulk CSVs are mostly ASCII with occasional Windows-1252 bytes
    # (e.g. 0x96 en dash) deep in the file, so it misdetects them as ASCII.
    try:
        text = data.content.decode("utf-8")
    except UnicodeDecodeError:
        text = data.content.decode("cp1252", errors="replace")
    return csv.DictReader(StringIO(text))


Listing = collections.namedtuple("Listing", "mtime size filename")


def parse_directory_listing(text):
    files = []

    dir_re = r"^(\d\d-\d\d-\d\d\s+\d\d:\d\d(AM|PM))\s+(\d+)\s+(.*\.htm)\s+$"
    for match in re.finditer(dir_re, text, re.MULTILINE):
        mtime = datetime.datetime.strptime(match.group(1), "%m-%d-%y %I:%M%p")
        files.append(
            Listing(mtime=mtime, size=int(match.group(3)), filename=match.group(4))
        )

    return files
