# encoding=utf-8
import requests
from openstates.scrape import State
from .bills import IlBillScraper
from .events import IlEventScraper


class Illinois(State):
    scrapers = {"bills": IlBillScraper, "events": IlEventScraper}
    legislative_sessions = [
        {
            "name": "90th Regular Session",
            "identifier": "90th",
            "classification": "primary",
            "_scraped_name": "90th General Assembly (1997-1998)",
            "start_date": "1997-01-08",
            "end_date": "1999-01-12",
        },
        {
            "name": "91st Regular Session",
            "identifier": "91st",
            "classification": "primary",
            "_scraped_name": "91st General Assembly (1999-2000)",
            "start_date": "1999-01-13",
            "end_date": "2001-01-09",
        },
        {
            "name": "92nd Regular Session",
            "identifier": "92nd",
            "classification": "primary",
            "_scraped_name": "92nd General Assembly (2001-2002)",
            "start_date": "2001-01-10",
            "end_date": "2003-01-07",
        },
        {
            "name": "93rd Regular Session",
            "identifier": "93rd",
            "classification": "primary",
            "_scraped_name": "93rd General Assembly (2003-2004)",
            "start_date": "2003-01-08",
            "end_date": "2005-01-11",
        },
        {
            "name": "93rd Special Session",
            "identifier": "93rd-special",
            "classification": "special",
            "start_date": "2004-06-04",
            "end_date": "2004-07-24",
        },
        {
            "name": "94th Regular Session",
            "identifier": "94th",
            "classification": "primary",
            "_scraped_name": "94th General Assembly (2005-2006)",
            "start_date": "2005-01-12",
            "end_date": "2007-01-09",
        },
        {
            "name": "95th Regular Session",
            "identifier": "95th",
            "classification": "primary",
            "_scraped_name": "95th General Assembly (2007-2008)",
            "start_date": "2007-01-10",
            "end_date": "2009-01-13",
        },
        {
            "name": "95th Special Session",
            "identifier": "95th-special",
            "classification": "special",
            "start_date": "2007-07-05",
            "end_date": "2009-01-13",
        },
        {
            "name": "96th Regular Session",
            "identifier": "96th",
            "classification": "primary",
            "_scraped_name": "96th General Assembly (2009-2010)",
            "start_date": "2009-01-14",
            "end_date": "2011-01-11",
        },
        {
            "name": "96th Special Session",
            "identifier": "96th-special",
            "classification": "special",
            "start_date": "2009-06-03",
            "end_date": "2009-07-15",
        },
        {
            "name": "97th Regular Session",
            "identifier": "97th",
            "classification": "primary",
            "_scraped_name": "97th General Assembly (2011-2012)",
            "start_date": "2011-01-12",
            "end_date": "2013-01-08",
        },
        {
            "name": "98th Regular Session",
            "identifier": "98th",
            "classification": "primary",
            "_scraped_name": "98th General Assembly (2013-2014)",
            "start_date": "2013-01-09",
            "end_date": "2015-01-13",
        },
        {
            "name": "99th Regular Session",
            "identifier": "99th",
            "classification": "primary",
            "_scraped_name": "99th General Assembly (2015-2016)",
            "start_date": "2015-01-14",
            "end_date": "2017-01-10",
        },
        {
            "name": "100th Special Session",
            "identifier": "100th-special",
            "classification": "special",
            "_scraped_name": "100th General Assembly (2017-2018)",
            "start_date": "2017-06-21",
            "end_date": "2017-06-21",
        },
        {
            "name": "100th Regular Session",
            "identifier": "100th",
            "classification": "primary",
            "start_date": "2017-01-11",
            "end_date": "2019-01-18",
        },
        {
            "name": "101st Regular Session",
            "identifier": "101st",
            "start_date": "2019-01-09",
            "end_date": "2019-12-14",
            "classification": "primary",
            "_scraped_name": "101st General Assembly (2019-2020)",
        },
        # Leave this on until 2023-01-31,
        # IL has a history post-session governor actions
        {
            "_scraped_name": "102nd General Assembly (2021-2022)",
            "name": "102nd Regular Session",
            "identifier": "102nd",
            "start_date": "2021-01-13",
            "end_date": "2021-06-01",
            "classification": "primary",
            "active": False,
        },
        # check senate prez in session_details in bills.py
        # https://www.ilga.gov/house/schedules/2024_House_Spring_Session.pdf
        # {
        #     "name": "103rd Regular Session",
        #     "identifier": "103rd",
        #     "start_date": "2023-01-11",
        #     "end_date": "2024-05-24",
        #     "classification": "primary",
        #     "active": False,
        # },
        {
            "_scraped_name": "103rd General Assembly (2023-2024)",
            "name": "103rd Regular Session",
            "identifier": "103rd",
            "start_date": "2023-01-11",
            "end_date": "2024-05-24",
            "classification": "primary",
            "active": False,
        },
        {
            "_scraped_name": "104th General Assembly (2025-2026)",
            "name": "104th Regular Session",
            "identifier": "104th",
            "start_date": "2025-01-08",
            "end_date": "2025-05-31",
            "classification": "primary",
            "active": True,
        },
    ]

    ignored_scraped_sessions = [
        "89th General Assembly (1995-1996)",
        "88th General Assembly (1993-1994)",
        "87th General Assembly (1991-1992)",
        "86th General Assembly (1989-1990)",
        "85th General Assembly (1987-1988)",
        "84th General Assembly (1985-1986)",
        "83rd General Assembly (1983-1984)",
        "82nd General Assembly (1981-1982)",
        "81st General Assembly (1979-1980)",
        "80th General Assembly (1977-1978)",
        "79th General Assembly (1975-1976)",
        "78th General Assembly (1973-1974)",
        "77th General Assembly (1971-1972)",
    ]

    def get_session_list(self):
        response = requests.get(
            "https://ilga.gov/API/Legislation/GetGeneralAssemblies"
        )
        response.raise_for_status()
        session_list = [ga["gaLabel"] for ga in response.json()]

        return session_list
