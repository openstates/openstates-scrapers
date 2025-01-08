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
            "classification": "primary",
        },
        {
            "_scraped_name": "102nd Legislature 1st Special Session",
            "end_date": "2011-11-22",
            "identifier": "102S1",
            "name": "102nd Legislature, 1st Special Session (2011)",
            "start_date": "2011-11-01",
            "classification": "primary",
        },
        {
            "_scraped_name": "103rd Legislature 1st and 2nd Sessions",
            "end_date": "2014-05-30",
            "identifier": "103",
            "name": "103rd Legislature (2013-2014)",
            "start_date": "2013-01-08",
            "classification": "primary",
        },
        {
            "_scraped_name": "104th Legislature 1st and 2nd Sessions",
            "end_date": "2016-12-31",
            "identifier": "104",
            "name": "104th Legislature (2015-2016)",
            "start_date": "2015-01-07",
            "classification": "primary",
        },
        {
            "_scraped_name": "105th Legislature 1st and 2nd Sessions",
            "end_date": "2018-12-31",
            "identifier": "105",
            "name": "105th Legislature (2017-2018)",
            "start_date": "2017-01-04",
            "classification": "primary",
        },
        {
            "_scraped_name": "106th Legislature 1st and 2nd Sessions",
            "end_date": "2020-12-31",
            "identifier": "106",
            "name": "106th Legislature (2019-2020)",
            "start_date": "2019-01-09",
            "classification": "primary",
        },
        {
            "_scraped_name": "107th Legislature 1st and 2nd Sessions",
            "identifier": "107",
            "name": "107th Legislature (2021-2022)",
            "start_date": "2022-01-05",
            "end_date": "2022-04-20",
            "classification": "primary",
            "active": False,
        },
        {
            "_scraped_name": "107th Legislature 1st Special Session",
            "identifier": "107S1",
            "name": "107th Legislature 1st Special Session",
            "start_date": "2021-09-13",
            "end_date": "2022-09-14",
            "classification": "special",
            "active": False,
        },
        {
            "_scraped_name": "108th Legislature 1st and 2nd Sessions",
            "identifier": "108",
            "name": "108th Legislature (2023-2024)",
            "start_date": "2023-01-04",
            "end_date": "2024-04-19",
            "classification": "primary",
            "active": False,
        },
        {
            "_scraped_name": "108th Legislature 1st Special Session",
            "identifier": "108S1",
            "name": "108th Legislature First Special Session",
            "start_date": "2024-07-25",
            "end_date": "2024-07-31",
            "classification": "special",
            "active": False,
        },
        {
            "_scraped_name": "109th Legislature 1st and 2nd Sessions",
            "identifier": "109",
            "name": "109th Legislature (2025-2026)",
            "start_date": "2025-01-08",
            "end_date": "2026-04-19",
            "classification": "primary",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "101st Legislature 1st and 2nd Sessions",
        "101st Legislature 1st Special Session",
        "100th Legislature 1st and 2nd Sessions",
        "100th Leg. First Special Session",
        "All Legislative Sessions",
    ]

    def get_session_list(self):
        # SSL bad as of 2024-11-18
        return url_xpath(
            "https://nebraskalegislature.gov/bills/",
            "//select[@name='Legislature']/option/text()",
            verify=False,
        )[:-1]
