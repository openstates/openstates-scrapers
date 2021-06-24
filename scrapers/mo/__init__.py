import http
import email
from utils import url_xpath, State
from .bills import MOBillScraper
from .events import MOEventScraper

# from .votes import MOVoteScraper
# from .committees import MOCommitteeScraper


class Missouri(State):
    scrapers = {
        "bills": MOBillScraper,
        # 'votes': MOVoteScraper,
        "events": MOEventScraper,
        # 'committees': MOCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2019-05-17",
        },
        {
            "_scraped_name": "2019 1st Extraordinary Session",
            "classification": "primary",
            "identifier": "2019S1",
            "name": "2019 First Extraordinary Session",
            "start_date": "2019-09-09",
            "end_date": "2019-09-25",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "classification": "primary",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
            "end_date": "2020-05-15",
        },
        {
            "_scraped_name": "2020 1st Extraordinary Session",
            "classification": "primary",
            "identifier": "2020S1",
            "name": "2020 First Extraordinary Session",
            "start_date": "2020-07-27",
            # TODO: real end date when session is over
            "end_date": "2020-07-31",
        },
        {
            "_scraped_name": "2020 2nd Extraordinary Session",
            "classification": "primary",
            "identifier": "2020S2",
            "name": "2020 Second Extraordinary Session",
            "start_date": "2020-11-04",
            # TODO: real end date when session is over
            "end_date": "2020-11-12",
        },
        {
            "_scraped_name": "2021 Regular Session",
            "classification": "primary",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-06",
            "end_date": "2021-05-30",
        },
        {
            "_scraped_name": "2021 1st Extraordinary Session",
            "classification": "primary",
            "identifier": "2021S1",
            "name": "2021 1st Extraordinary Session",
            "start_date": "2021-06-23",
            # TODO: real end date when session is over
            "end_date": "2021-06-25",
        },
    ]
    ignored_scraped_sessions = [
        "2021 Regular Session",
        "2018 Regular Session",
        "2018 Special Session",
        "2018 1st Extraordinary Session",
        "2007 Regular Session",
        "2010 Extraordinary Session",
        "2002 Regular Session",
        "1999 Regular Session",
        "2013 Extraordinary Session",
        "2007 Extraordinary Session",
        "2003 2nd Extraordinary Session",
        "2014 Regular Session",
        "2017 Extraordinary Session",
        "2005 Regular Session",
        "2011 Extraordinary Session",
        "2006 Regular Session",
        "2004 Regular Session",
        "2015 Regular Session",
        "2003 1st Extraordinary Session",
        "2010 Regular Session",
        "2001 Regular Session",
        "2017 2nd Extraordinary Session",
        "2003 Regular Session",
        "2009 Regular Session",
        "2005 Extraordinary Session",
        "2017 Regular Session",
        "2000 Regular Session",
        "2013 Regular Session",
        "2011 Regular Session",
        "2001 Extraordinary Session",
        "2012 Regular Session",
        "2008 Regular Session",
        "2016 Regular Session",
        "2019 1st Extraordinary Session",
    ]

    def get_session_list(self):
        http.client.parse_headers = parse_headers_override
        return url_xpath(
            "https://www.house.mo.gov/billcentral.aspx?year=2019&code=S1&q=&id=",
            '//select[@id="SearchSession"]/option/text()',
        )


def parse_headers_override(fp, _class=http.client.HTTPMessage):
    _MAXLINE = 2000
    _MAXHEADERS = 2000
    # based on Python's implementation but built to ignore bad headers
    headers = []
    while True:
        line = fp.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise ValueError("header line")

        # there is a bad header named default-src that has no colon, just skip it
        if line.startswith(b"default-src"):
            continue

        headers.append(line)
        if len(headers) > _MAXHEADERS:
            raise ValueError("got more than %d headers" % _MAXHEADERS)
        if line in (b"\r\n", b"\n", b""):
            break
    hstring = b"".join(headers).decode("iso-8859-1")
    return email.parser.Parser(_class=_class).parsestr(hstring)
