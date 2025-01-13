import requests
from openstates.scrape import State
from .bills import PRBillScraper
from .votes import PRVoteScraper
import re
import json


settings = dict(SCRAPELIB_TIMEOUT=600)


class PuertoRico(State):
    scrapers = {
        "bills": PRBillScraper,
        "votes": PRVoteScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-2012",
            "identifier": "2009-2012",
            "name": "2009-2012 Session",
            "start_date": "2009-01-14",
            "end_date": "2013-01-08",
        },
        {
            "_scraped_name": "2013-2016",
            "identifier": "2013-2016",
            "name": "2013-2016 Session",
            "start_date": "2013-01-14",
            "end_date": "2017-01-08",
        },
        {
            "_scraped_name": "2017-2020",
            "identifier": "2017-2020",
            "name": "2017-2020 Session",
            "start_date": "2017-01-09",
            "end_date": "2020-12-31",
        },
        {
            "_scraped_name": "2021-2024",
            "identifier": "2021-2024",
            "name": "2021-2024 Session",
            "start_date": "2021-01-11",
            "end_date": "2024-12-31",
            "active": False,
        },
        {
            "_scraped_name": "2025-2028",
            "identifier": "2025-2028",
            "name": "2025-2028 Session",
            "start_date": "2025-01-13",
            "end_date": "2028-12-31",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "2005-2008",
        "2001-2004",
        "1997-2000",
        "1993-1996",
        "1989-1992",
        "1985-1988",
    ]

    def get_session_list(self):
        s = requests.Session()
        # this URL should work even for future sessions
        url = "https://sutra.oslpr.org/"

        headers = {
            "accept": "text/x-component",
            "content-type": "text/plain;charset=UTF-8",
            "next-action": "703ccedd8bdfbce1899c7590dfae240ff1aa6d2d2f",
            "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(public)%22%2C%7B%22children%22%3A%5B%22(landing)%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2F%22%2C%22refresh%22%5D%7D%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
            "origin": url,
            "referer": url,
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }
        data = '["/cuatrienios"]'
        data = s.post(
            "https://sutra.oslpr.org/", headers=headers, data=data, verify=False
        )
        sdata = re.search(r"1:(.*?}])", data.text).group(1)
        json_data = json.loads(sdata)
        sessions = []
        for data in json_data:
            descripcion = data["descripcion"]
            sessions.append(descripcion)
        return sessions
