from utils import url_xpath, State
from .bills import KSBillScraper
from .events import KSEventScraper


# Kansas API's 429 error response includes:
# You have received this notification because this IP address is querying
# the kslegislature.org website at a high rate. If the queries are generated
# by an automated tool, please introduce a delay rate of 3-5 seconds between queries.
settings = dict(SCRAPELIB_TIMEOUT=300, SCRAPELIB_RPM=12)


class Kansas(State):
    scrapers = {
        "bills": KSBillScraper,
        "events": KSEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "b2011_12",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-12",
            "end_date": "2012-05-14",
        },
        {
            "_scraped_name": "b2013_14",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2014-05-30",
        },
        {
            "_scraped_name": "b2015_16",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2016-06-01",
        },
        {
            "_scraped_name": "b2017_18",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2018-04-07",
        },
        {
            "_scraped_name": "b2019_20",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2020-05-31",
        },
        {
            "_scraped_name": "b2020s",
            "classification": "special",
            "identifier": "2020S1",
            "name": "2020 Special Session",
            "start_date": "2019-06-03",
            "end_date": "2020-06-05",
        },
        {
            "_scraped_name": "b2021_22",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-11",
            # TODO: set real end date
            "end_date": "2022-05-31",
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        url = url_xpath(
            "http://www.kslegislature.org/li",
            '//div[@id="nav"]//a[contains(text(), "Senate Bills")]/@href',
        )[0]
        return [url.split("/")[2]]
