from utils import url_xpath
from openstates.scrape import State
from .bills import NEBillScraper
from .events import NEEventScraper


class Nebraska(State):
    scrapers = {
        "bills": NEBillScraper,
        "events": NEEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "102nd Legislature 1st and 2nd Sessions",
            "end_date": "2012-04-18",
            "identifier": "102",
            "name": "102nd Legislature (2011-2012)",
            "start_date": "2011-01-05",
        },
        {
            "_scraped_name": "102nd Legislature 1st Special Session",
            "end_date": "2011-11-22",
            "identifier": "102S1",
            "name": "102nd Legislature, 1st Special Session (2011)",
            "start_date": "2011-11-01",
        },
        {
            "_scraped_name": "103rd Legislature 1st and 2nd Sessions",
            "end_date": "2014-05-30",
            "identifier": "103",
            "name": "103rd Legislature (2013-2014)",
            "start_date": "2013-01-08",
        },
        {
            "_scraped_name": "104th Legislature 1st and 2nd Sessions",
            "end_date": "2016-12-31",
            "identifier": "104",
            "name": "104th Legislature (2015-2016)",
            "start_date": "2015-01-07",
        },
        {
            "_scraped_name": "105th Legislature 1st and 2nd Sessions",
            "end_date": "2018-12-31",
            "identifier": "105",
            "name": "105th Legislature (2017-2018)",
            "start_date": "2017-01-04",
        },
        {
            "_scraped_name": "106th Legislature 1st and 2nd Sessions",
            "end_date": "2020-12-31",
            "identifier": "106",
            "name": "106th Legislature (2019-2020)",
            "start_date": "2019-01-04",
        },
        {
            "_scraped_name": "107th Legislature 1st and 2nd Sessions",
            "identifier": "107",
            "name": "107th Legislature (2021-2022)",
            "start_date": "2021-01-06",
            "end_date": "2021-12-31",
            "active": True,
        },
        {
            "_scraped_name": "107th Legislature 1st Special Session",
            "identifier": "107S1",
            "name": "107th Legislature 1st Special Session",
            "start_date": "2021-09-13",
            "end_date": "2021-09-30",
            "classification": "special",
            "active": False,
        },
    ]
    ignored_scraped_sessions = [
        "101st Legislature 1st and 2nd Sessions",
        "101st Legislature 1st Special Session",
        "100th Legislature 1st and 2nd Sessions",
        "100th Leg. First Special Session",
    ]

    def get_session_list(self):
        return url_xpath(
            "https://nebraskalegislature.gov/bills/",
            "//select[@name='Legislature']/option/text()",
        )[:-1]
