import os
import requests
from openstates.utils import State
from .people import INPersonScraper
from .bills import INBillScraper

# from .committees import INCommitteeScraper


class Indiana(State):
    scrapers = {
        "people": INPersonScraper,
        # 'committees': INCommitteeScraper,
        "bills": INBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "First Regular Session 116th General Assembly (2009)",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2009-01-07",
            "end_date": "2009-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 116th General Assembly (2010)",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-05",
            "end_date": "2010-03-12",
        },
        {
            "_scraped_name": "First Regular Session 117th General Assembly (2011)",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2011-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 117th General Assembly (2012)",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-04",
            "end_date": "2012-03-014",
        },
        {
            "_scraped_name": "First Regular Session 118th General Assembly (2013)",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-07",
            "end_date": "2013-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 118th General Assembly (2014)",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-06",
            "end_date": "2014-03-14",
        },
        {
            "_scraped_name": "First Regular Session 119th General Assembly (2015)",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06",
            "end_date": "2015-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 119th General Assembly (2016)",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05",
            "end_date": "2016-03-10",
        },
        {
            "_scraped_name": "First Regular Session 120th General Assembly (2017)",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2017-04-29",
        },
        {
            "_scraped_name": "Second Regular Session 120th General Assembly (2018)",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02",
            "end_date": "2018-03-16",
        },
        {
            "_scraped_name": "Special Session 120th General Assembly (2018)",
            "identifier": "2018ss1",
            "name": "2018 Special Session",
            "start_date": "2018-05-14",
            "end_date": "2018-05-24",
        },
        {
            "_scraped_name": "First Regular Session 121st General Assembly (2019)",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2019-04-24",
        },
        {
            "_scraped_name": "Second Regular Session 121st General Assembly (2020)",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-06",
            "end_date": "2020-03-11",
        },
    ]
    ignored_scraped_sessions = [
        "First Regular Session 121st General Assembly (2019)",
        "2012 Regular Session",
        "2011 Regular Session",
        "2010 Regular Session",
        "2009 Special Session",
        "2009 Regular Session",
        "2008 Regular Session",
        "2007 Regular Session",
        "2006 Regular Session",
        "2005 Regular Session",
        "2004 Regular Session",
        "2003 Regular Session",
        "2002 Special Session",
        "2002 Regular Session",
        "2001 Regular Session",
        "2000 Regular Session",
        "1999 Regular Session",
        "1998 Regular Session",
        "1997 Regular Session",
    ]

    def get_session_list(self):
        apikey = os.environ["INDIANA_API_KEY"]
        useragent = os.getenv("USER_AGENT", "openstates")
        headers = {
            "Authorization": apikey,
            "Accept": "application/json",
            "User-Agent": useragent,
        }
        resp = requests.get("https://api.iga.in.gov/sessions", headers=headers)
        resp.raise_for_status()
        return [session["name"] for session in resp.json()["items"]]
