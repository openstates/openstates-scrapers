import re
import time
import datetime
import collections
import csv
from io import StringIO


class EmptyCSVError(Exception):
    """Raised when a CT CSV download returns an empty or headerless body.

    CT serves its bulk data over a slow FTP server, and FTP transfers
    (especially through a proxy) intermittently return a zero-byte or
    truncated body. When that happens, csv.DictReader has no header row and
    every ``row["<column>"]`` lookup raises a misleading ``KeyError``. This
    exception makes the real cause (an empty download) explicit so callers
    can retry instead.
    """


def open_csv(data, expected_fields=None):
    # Don't rely on chardet here: it only samples the first 200KB by default,
    # and CT's bulk CSVs are mostly ASCII with occasional Windows-1252 bytes
    # (e.g. 0x96 en dash) deep in the file, so it misdetects them as ASCII.
    #
    # Decode with "utf-8-sig" (not plain "utf-8"): CT prepends a UTF-8 BOM
    # (EF BB BF) to these files. Plain utf-8 keeps the BOM as a leading
    # \ufeff, which glues onto the first header -- turning "comm_code" into
    # '\ufeff"comm_code"' and breaking every row["comm_code"] lookup.
    try:
        text = data.content.decode("utf-8-sig")
    except UnicodeDecodeError:
        # cp1252 has no notion of a BOM, so strip a stray one defensively.
        text = data.content.decode("cp1252", errors="replace").lstrip("\ufeff")

    if not text.strip():
        raise EmptyCSVError("CSV download returned an empty body")

    reader = csv.DictReader(StringIO(text))

    # A valid CT CSV always has a header row; an empty/truncated FTP transfer
    # yields no fieldnames, which would otherwise surface as a cryptic KeyError
    # deep in the caller.
    if not reader.fieldnames:
        raise EmptyCSVError("CSV download has no header row")

    if expected_fields:
        missing = [f for f in expected_fields if f not in reader.fieldnames]
        if missing:
            raise EmptyCSVError(
                "CSV download missing expected column(s): {} (got: {})".format(
                    ", ".join(missing), ", ".join(reader.fieldnames)
                )
            )

    return reader


def fetch_csv(scraper, url, expected_fields=None, retries=3, backoff=5):
    """Fetch a CT CSV over (flaky) FTP and parse it, retrying on empty bodies.

    CT's FTP server occasionally returns a zero-byte/truncated response. Each
    attempt re-issues the HTTP/FTP request on a fresh connection via
    ``scraper.get`` so a retry actually pulls new bytes rather than re-parsing
    the same empty payload.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        data = scraper.get(url)
        try:
            return open_csv(data, expected_fields=expected_fields)
        except EmptyCSVError as exc:
            last_error = exc
            scraper.logger.warning(
                "Empty/invalid CSV from %s (attempt %s/%s): %s",
                url,
                attempt,
                retries,
                exc,
            )
            if attempt < retries:
                time.sleep(backoff)

    raise EmptyCSVError(
        "CSV download from {} still empty/invalid after {} attempts: {}".format(
            url, retries, last_error
        )
    )


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
