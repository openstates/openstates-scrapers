from utils import url_xpath, State
from .bills import OHBillScraper

# from .events import OHEventScraper


class Ohio(State):
    scrapers = {
        # 'events': OHEventScraper,
        "bills": OHBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "128",
            "identifier": "128",
            "name": "128th Legislature (2009-2010)",
            "start_date": "2009-01-05",
            "end_date": "2010-12-31",
        },
        {
            "_scraped_name": "129",
            "identifier": "129",
            "name": "129th Legislature (2011-2012)",
            "start_date": "2011-01-03",
            "end_date": "2012-12-31",
        },
        {
            "_scraped_name": "130",
            "identifier": "130",
            "name": "130th Legislature (2013-2014)",
            "start_date": "2013-01-07",
            "end_date": "2014-12-31",
        },
        {
            "_scraped_name": "131 (2015-2016)",
            "identifier": "131",
            "name": "131st Legislature (2015-2016)",
            "start_date": "2015-01-05",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "132 (2017-2018)",
            "identifier": "132",
            "name": "132st Legislature (2017-2018)",
            "start_date": "2017-01-02",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "133 (2019-2020)",
            "identifier": "133",
            "name": "133rd Legislature (2019-2020)",
            "start_date": "2019-01-07",
            "end_date": "2020-12-31",
        },
        {
            "_scraped_name": "134 (2021-2022)",
            "identifier": "134",
            "name": "134th Legislature (2021-2022)",
            "start_date": "2021-01-04",
            "end_date": "2022-12-31",
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        sessions = url_xpath(
            "https://www.legislature.ohio.gov/legislation/search"
            "?generalAssemblies=133&pageSize=10&start=1&isInitial=true",
            '//div[@id="generalAssemblyValues"]//'
            'div[contains(@class, "optionLabel")]/text()',
            user_agent="openstates 2021",
        )
        # Archive does not include current session
        return sessions
