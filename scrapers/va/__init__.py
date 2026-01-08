import logging
from openstates.scrape import State
from .csv_bills import VaCSVBillScraper
from .events import VaEventScraper
from .bills import VaBillScraper

import requests

logging.getLogger(__name__).addHandler(logging.NullHandler())


settings = {"SCRAPELIB_RPM": 40}


class Virginia(State):
    scrapers = {
        "events": VaEventScraper,
        "csv_bills": VaCSVBillScraper,
        "bills": VaBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2010 Session",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-13",
            "end_date": "2010-03-13",
        },
        {
            "_scraped_name": "2011 Session",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-12",
            "end_date": "2011-03-27",
        },
        {
            "_scraped_name": "2011 Special Session I",
            "identifier": "2011specialI",
            "name": "2011, 1st Special Session",
            "start_date": "2011-06-09",
            "end_date": "2011-07-29",
        },
        {
            "_scraped_name": "2012 Session",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11",
            "end_date": "2012-03-10",
        },
        {
            "_scraped_name": "2012 Special Session I",
            "identifier": "2012specialI",
            "name": "2012, 1st Special Session",
            "start_date": "2012-03-10",
            "end_date": "2012-06-20",
        },
        {
            "_scraped_name": "2013 Session",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2013-02-25",
        },
        {
            "_scraped_name": "2013 Special Session I",
            "identifier": "2013specialI",
            "name": "2013, 1st Special Session",
            "start_date": "2013-04-03",
            "end_date": "2013-04-03",
        },
        {
            "_scraped_name": "2014 Session",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-09",
            "end_date": "2014-03-10",
        },
        {
            "_scraped_name": "2014 Special Session I",
            "identifier": "2014specialI",
            "name": "2014, 1st Special Session",
            "start_date": "2014-03-24",
            "end_date": "2015-01-14",
        },
        {
            "_scraped_name": "2015 Session",
            "end_date": "2015-02-27",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-14",
            "end_date": "2015-02-27",
        },
        {
            "_scraped_name": "2015 Special Session I",
            "identifier": "2015specialI",
            "name": "2015, 1st Special Session",
            "start_date": "2015-08-17",
            "end_date": "2015-08-17",
        },
        {
            "_scraped_name": "2016 Session",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-13",
            "end_date": "2016-03-12",
        },
        {
            "_scraped_name": "2017 Session",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-02-25",
        },
        {
            "_scraped_name": "2018 Session",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-10",
        },
        {
            "_scraped_name": "2018 Special Session I",
            "identifier": "2018specialI",
            "name": "2018, 1st Special Session",
            "start_date": "2018-04-11",
            "end_date": "2018-05-30",
        },
        {
            "_scraped_name": "2018 Special Session II",
            "identifier": "2018specialI",
            "name": "2018, 2nd Special Session",
            "start_date": "2018-08-30",
            "end_date": "2018-11-30",
        },
        {
            "_scraped_name": "2019 Session",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2019-02-24",
        },
        {
            "_scraped_name": "2019 Special Session I",
            "identifier": "2019specialI",
            "name": "2019, 1st Special Session",
            "start_date": "2019-07-09",
            "end_date": "2019-07-09",
        },
        {
            "_scraped_name": "2020 Session",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
            "end_date": "2020-03-12",
        },
        {
            "_scraped_name": "2020 Special Session I",
            "identifier": "2020specialI",
            "name": "2020, 1st Special Session",
            "start_date": "2020-08-18",
            "end_date": "2020-11-09",
        },
        {
            "_scraped_name": "2021 Session",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-13",
            "end_date": "2021-03-08",
        },
        {
            "_scraped_name": "2021 Special Session II",
            "classification": "special",
            "identifier": "2021S2",
            "name": "2021, 2nd Special Session",
            "start_date": "2021-08-02",
            "end_date": "2021-11-01",
        },
        {
            "_scraped_name": "2022 Session",
            "identifier": "2022",
            "name": "2022 Regular Session",
            "start_date": "2022-01-12",
            "end_date": "2022-03-12",
            "active": False,
        },
        {
            "_scraped_name": "2022 Special Session I",
            "classification": "special",
            "identifier": "2022S1",
            "name": "2022, 1st Special Session",
            "start_date": "2022-04-04",
            "end_date": "2022-05-04",
            "active": False,
        },
        {
            "_scraped_name": "2023 Session",
            "classification": "primary",
            "identifier": "2023",
            "name": "2023 Regular Session",
            "start_date": "2023-01-11",
            "end_date": "2023-03-11",
            "active": False,
        },
        {
            "_scraped_name": "2023 Special Session I",
            "classification": "special",
            "identifier": "2023S1",
            "name": "2023, 1st Special Session",
            "start_date": "2023-08-05",
            "end_date": "2023-08-13",
            "active": False,
        },
        {
            "_scraped_name": "2024 Session",
            "identifier": "2024",
            "name": "2024 Regular Session",
            "start_date": "2024-01-10",
            "end_date": "2024-03-09",
            "active": False,
        },
        {
            "_scraped_name": "2024 Special Session I",
            "classification": "special",
            "identifier": "2024S1",
            "name": "2024, 1st Special Session",
            "start_date": "2024-05-13",
            # TODO: update actual end date
            "end_date": "2024-05-20",
            "active": False,
        },
        {
            "_scraped_name": "2025 Regular Session",
            "identifier": "2025",
            "name": "2025 Regular Session",
            "start_date": "2025-01-08",
            "end_date": "2025-02-22",
            "active": False,
            "extras": {"session_code": "20251"},
        },
        {
            "_scraped_name": "2026 Regular Session",
            "identifier": "2026",
            "name": "2026 Regular Session",
            "start_date": "2026-01-14",
            "end_date": "2026-03-14",
            "active": True,
            "extras": {"session_code": "20261"},
        },
    ]
    ignored_scraped_sessions = [
        "2025 Session",
        "2021 Special Session I",
        "2015 Special Session I",
        "2015 Session",
        "2014 Special Session I",
        "2014 Session",
        "2013 Special Session I",
        "2013 Session",
        "2012 Special Session I",
        "2012 Session",
        "2011 Special Session I",
        "2011 Session",
        "2010 Session",
        "2009 Session",
        "2009 Special Session I",
        "2008 Session",
        "2008 Special Session I",
        "2008 Special Session II",
        "2007 Session",
        "2006 Session",
        "2006 Special Session I",
        "2005 Session",
        "2004 Session",
        "2004 Special Session I",
        "2004 Special Session II",
        "2003 Session",
        "2002 Session",
        "2001 Session",
        "2001 Special Session I",
        "2000 Session",
        "1999 Session",
        "1998 Session",
        "1998 Special Session I",
        "1997 Session",
        "1996 Session",
        "1995 Session",
        "1994 Session",
        "1994 Special Session I",
        "1994 Special Session II",
    ]

    def get_session_list(self):
        headers = {
            "x-oxylabs-force-headers": "1",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://lis.virginia.gov/bill-search",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "WebAPIKey": "FCE351B6-9BD8-46E0-B18F-5572F4CCA5B9",
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
        }
        response = requests.get(
            "https://lis.virginia.gov/Session/api/GetSessionListAsync/",
            verify=False,
            headers=headers,
        ).json()
        session_list = []
        for row in response["Sessions"]:
            session_list.append(f"{row['SessionYear']} {row['DisplayName']}")
        return session_list
