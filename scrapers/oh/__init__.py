from utils import url_xpath
from openstates.scrape import State
from .bills import OHBillScraper

from .events import OHEventScraper


class Ohio(State):
    scrapers = {
        "events": OHEventScraper,
        "bills": OHBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "131st (2015-2016)",
            "identifier": "131",
            "name": "131st Legislature (2015-2016)",
            "start_date": "2015-01-05",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "132nd (2017-2018)",
            "identifier": "132",
            "name": "132st Legislature (2017-2018)",
            "start_date": "2017-01-02",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "133rd (2019-2020)",
            "identifier": "133",
            "name": "133rd Legislature (2019-2020)",
            "start_date": "2019-01-07",
            "end_date": "2020-12-31",
        },
        {
            "_scraped_name": "134th (2021-2022)",
            "identifier": "134",
            "name": "134th Legislature (2021-2022)",
            "start_date": "2021-01-04",
            "end_date": "2022-12-31",
            "active": False,
        },
        {
            "_scraped_name": "135th (2023-2024)",
            "identifier": "135",
            "name": "135th Legislature (2023-2024)",
            "start_date": "2023-01-02",
            "end_date": "2024-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        sessions = url_xpath(
            "https://www.legislature.ohio.gov/legislation/search"
            "?generalAssemblies=135&pageSize=10&start=1&isInitial=true",
            '//div[@id="general-assembly-radio-selector"]//'
            'label[contains(@class, "radio-choice-option")]/span[1]/text()',
            user_agent="openstates 2021",
        )
        return sessions
