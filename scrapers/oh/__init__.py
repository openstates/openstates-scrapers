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
            "_scraped_name": "135th - Special Session (2024)",
            "classification": "special",
            "identifier": "135S1",
            "name": "135th Legislature, First Special Session",
            "start_date": "2024-05-28",
            "end_date": "2024-06-12",
            "active": False,
            "extras": {"session_id": "135_special_1", "session_url_slug": "135-s1"},
        },
        {
            "_scraped_name": "135th (2023-2024)",
            "identifier": "135",
            "name": "135th Legislature (2023-2024)",
            "start_date": "2023-01-02",
            "end_date": "2024-12-31",
            "active": False,
        },
        {
            "_scraped_name": "136th (2025-2026)",
            "identifier": "136",
            "name": "136th Legislature (2025-2026)",
            "start_date": "2025-01-06",
            "end_date": "2026-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "130th (2013-2014)",
        "129th (2011-2012)",
        "128th (2009-2010)",
        "127th (2007-2008)",
        "126th (2005-2006)",
        "125th - Special Session (2004)",
        "125th (2003-2004)",
        "124th (2001-2002)",
        "123rd (1999-2000)",
        "122nd (1997-1998)",
    ]

    def get_session_list(self):
        sessions = url_xpath(
            "https://www.legislature.ohio.gov/legislation/search"
            "?generalAssemblies=135&pageSize=10&start=1&isInitial=true",
            '//div[@id="general-assembly-radio-selector"]//'
            'label[contains(@class, "radio-choice-option")]/span[1]/text()',
            user_agent="openstates 2021",
        )
        return sessions
