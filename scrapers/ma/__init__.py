import re
import requests
import lxml.html
from openstates.scrape import State
from .bills import MABillScraper
from .events import MAEventScraper
from .votes import MAVoteScraper


class Massachusetts(State):
    scrapers = {
        "bills": MABillScraper,
        "events": MAEventScraper,
        "votes": MAVoteScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "186th",
            "classification": "primary",
            "identifier": "186th",
            "name": "186th Legislature (2009-2010)",
            "start_date": "2009-01-07",
            "end_date": "2010-07-31",
        },
        {
            "_scraped_name": "187th",
            "classification": "primary",
            "identifier": "187th",
            "name": "187th Legislature (2011-2012)",
            "start_date": "2011-01-05",
            "end_date": "2012-07-31",
        },
        {
            "_scraped_name": "188th",
            "classification": "primary",
            "identifier": "188th",
            "name": "188th Legislature (2013-2014)",
            "start_date": "2013-01-02",
            "end_date": "2014-08-01",
        },
        {
            "_scraped_name": "189th",
            "classification": "primary",
            "identifier": "189th",
            "name": "189th Legislature (2015-2016)",
            "start_date": "2015-01-07",
            "end_date": "2016-07-31",
        },
        {
            "_scraped_name": "190th",
            "classification": "primary",
            "identifier": "190th",
            "name": "190th Legislature (2017-2018)",
            "start_date": "2017-01-04",
            "end_date": "2018-12-31",
        },
        {
            "_scraped_name": "191st",
            "classification": "primary",
            "identifier": "191st",
            "name": "191st Legislature (2019-2020)",
            "start_date": "2019-01-02",
            "end_date": "2021-01-06",
        },
        {
            "_scraped_name": "192nd",
            "classification": "primary",
            "identifier": "192nd",
            "name": "192nd Legislature (2021-2022)",
            "start_date": "2021-01-06",
            "end_date": "2021-12-31",
            "active": False,
        },
        {
            "_scraped_name": "193rd",
            "classification": "primary",
            "identifier": "193rd",
            "name": "193rd Legislature (2023-2024)",
            "start_date": "2023-01-04",
            "end_date": "2024-07-31",  # https://malegislature.gov/ClerksOffice/Senate/Deadlines
            "active": True,
        },
    ]
    ignored_scraped_sessions = []

    def get_session_list(self):
        doc = lxml.html.fromstring(
            requests.get("https://malegislature.gov/Bills/Search", verify=False).text
        )
        sessions = doc.xpath(
            "//div[@data-refinername='lawsgeneralcourt']/div/label/text()"
        )

        # Remove all text between parens, like (Current) (7364)
        return list(
            filter(
                None,
                [re.sub(r"\([^)]*\)", "", session).strip() for session in sessions],
            )
        )
