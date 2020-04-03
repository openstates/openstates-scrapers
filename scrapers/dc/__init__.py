from openstates.utils import State
from .people import DCPersonScraper
from .bills import DCBillScraper
from .utils import api_request

# from .committees import DCCommitteeScraper
# from .events import DCEventScraper


class DistrictOfColumbia(State):
    scrapers = {
        "people": DCPersonScraper,
        # 'committees': DCCommitteeScraper,
        # 'events': DCEventScraper,
        "bills": DCBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "19",
            "identifier": "19",
            "name": "19th Council Period (2011-2012)",
            "start_date": "2011-01-01",
            "end_date": "2012-12-31",
        },
        {
            "_scraped_name": "20",
            "identifier": "20",
            "name": "20th Council Period (2013-2014)",
            "start_date": "2013-01-01",
            "end_date": "2014-12-31",
        },
        {
            "_scraped_name": "21",
            "identifier": "21",
            "name": "21st Council Period (2015-2016)",
            "start_date": "2015-01-01",
            "end_date": "2016-12-31",
        },
        {
            "_scraped_name": "22",
            "identifier": "22",
            "name": "22nd Council Period (2017-2018)",
            "start_date": "2017-01-01",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "23",
            "identifier": "23",
            "name": "23rd Council Period (2019-2020)",
            "start_date": "2019-01-02",
            "end_date": "2020-12-31",
        },
    ]
    ignored_scraped_sessions = [
        "18",
        "17",
        "16",
        "15",
        "14",
        "13",
        "12",
        "11",
        "10",
        "9",
        "8",
    ]

    def get_session_list(self):
        data = api_request("/LIMSLookups")
        return [c["Prefix"] for c in data["d"]["CouncilPeriods"]]
