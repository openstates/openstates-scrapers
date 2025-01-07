import requests
import lxml.html
from openstates.scrape import State
from .bills import PRBillScraper
from .votes import PRVoteScraper

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
            "active": True,
        },
        {
            "_scraped_name": "2025-2028",
            "identifier": "2025-2028",
            "name": "2025-2028 Session",
            "start_date": "2025-01-13",
            "end_date": "2028-12-31",
            "active": False,
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
        url = "https://sutra.oslpr.org/osl/esutra/"

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/79.0.3945.117 Safari/537.36",
            "referer": url,
            "origin": "https://sutra.oslpr.org",
            "authority": "sutra.oslpr.org",
        }

        data = s.get(url, headers=headers, verify=False)

        doc = lxml.html.fromstring(data.text)
        sessions = doc.xpath(
            "//select[@id='ctl00_CPHBody_Tramites_lovCuatrienio']/option/text()"
        )
        return sessions
