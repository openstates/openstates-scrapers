import pytz
import urllib.parse


def index_legislators(scraper, session_key):
    """
    Get the full name of legislators. The membership API only returns a "LegislatorCode".
    This will cross-reference the name.
    """
    legislators_response = scraper.api_client.get("legislators", session=session_key)

    legislators = {}
    for leg in legislators_response:
        legislators[leg["LegislatorCode"]] = "{} {}".format(
            leg["FirstName"], leg["LastName"]
        )

    return legislators


def get_timezone():
    return pytz.timezone("US/Pacific")


def url_fix(s):
    # Adapted from werkzeug.utils (https://bit.ly/3aPRHjv)
    """Sometimes you get an URL by a user that just isn't a real URL because
    it contains unsafe characters like ' ' and so on. This function can fix
    some of the problems in a similar way browsers handle data entered by the
    user:

    :param s: the string with the URL to fix.
    """
    url = urllib.parse.urlparse(s)
    path = urllib.parse.quote(url.path, safe="/%+$!*'(),")
    return urllib.parse.urlunsplit(
        (url.scheme, url.netloc, path, url.query, url.fragment)
    )


SESSION_KEYS = {
    "2017 Regular Session": "2017R1",
    "2018 Regular Session": "2018R1",
    "2018 Special Session": "2018S1",
    "2019 Regular Session": "2019R1",
    "2020 Regular Session": "2020R1",
    "2020S1": "2020S1",
    "2020S2": "2020S2",
    "2020S3": "2020S3",
    "2021 Regular Session": "2021R1",
}
