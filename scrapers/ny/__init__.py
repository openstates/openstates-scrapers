from utils import url_xpath, State

from .bills import NYBillScraper
from .events import NYEventScraper
from .people import NYPersonScraper

# from .committees import NYCommitteeScraper


settings = dict(SCRAPELIB_TIMEOUT=120)


class NewYork(State):
    scrapers = {
        "bills": NYBillScraper,
        "events": NYEventScraper,
        "people": NYPersonScraper,
        # 'committees': NYCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009",
            "identifier": "2009-2010",
            "name": "2009 Regular Session",
            "start_date": "2009-01-07",
            "end_date": "2010-12-31",
        },
        {
            "_scraped_name": "2011",
            "identifier": "2011-2012",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2012-12-31",
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013-2014",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2014-12-31",
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015-2016",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017-2018",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019-2020",
            "name": "2019 Regular Session",
            "start_date": "2019-01-03",
            "end_date": "2020-12-31",
        },
        {
            "_scraped_name": "2021",
            "identifier": "2021-2022",
            "name": "2021 Regular Session",
            "start_date": "2021-01-06",
            "end_date": "2022-12-31",
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        return url_xpath(
            "http://nysenate.gov/search/legislation",
            '//select[@name="bill_session_year"]/option[@value!=""]/@value',
        )
