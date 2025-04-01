import re
import logging
import requests
import lxml.html
from openstates.scrape import State
from .bills import MABillScraper
from .events import MAEventScraper
from .votes import MAVoteScraper

logger = logging.getLogger("openstates")


def get_fallback_hardcoded_sessions(url):
    logger.warning(f"Got a 500 Error on : {url}, using hard coded session list")
    hard_coded_session_list = [
        "184th",
        "185th",
        "186th",
        "187th",
        "188th",
        "189th",
        "190th",
        "191st",
        "192nd",
        "193rd",
        "194th",
    ]
    return list(hard_coded_session_list)


class Massachusetts(State):
    scrapers = {
        "bills": MABillScraper,
        "events": MAEventScraper,
        "votes": MAVoteScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "184th",
            "classification": "primary",
            "identifier": "184th",
            "name": "184th Legislature (2007-2008)",
            "start_date": "2005-01-01",  # est
            "end_date": "2006-07-31",  # est
            "active": False,
        },
        {
            "_scraped_name": "185th",
            "classification": "primary",
            "identifier": "185th",
            "name": "185th Legislature (2007-2008)",
            "start_date": "2007-01-01",  # est
            "end_date": "2008-07-31",  # est
            "active": False,
        },
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
            "active": False,
        },
        {
            "_scraped_name": "194th",
            "classification": "primary",
            "identifier": "194th",
            "name": "194th Legislature (2025-2026)",
            "start_date": "2025-01-01",
            "end_date": "2026-07-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = ["185th"]

    def get_session_list(self):
        url = "https://malegislature.gov/Bills/Search"
        try:
            response = requests.get(url, verify=False)
            if response.status_code == 500:
                sessions = get_fallback_hardcoded_sessions(url)
            else:
                doc = lxml.html.fromstring(response.text)
                sessions = doc.xpath(
                    "//div[@data-refinername='lawsgeneralcourt']/div/label/text()"
                )

                # Remove all text between parens, like (Current) (7364)
                sessions = list(
                    filter(
                        None,
                        [
                            re.sub(r"\([^)]*\)", "", session).strip()
                            for session in sessions
                        ],
                    )
                )
        except requests.exceptions.ConnectionError:
            sessions = get_fallback_hardcoded_sessions(url)

        return sessions
