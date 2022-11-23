from openstates.scrape import State
from .util import get_client, backoff
from .bills import GABillScraper
from .events import GAEventScraper


class Georgia(State):
    scrapers = {
        "bills": GABillScraper,
        "events": GAEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011-2012 Regular Session",
            "identifier": "2011_12",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-10",
            "end_date": "2012-03-29",
        },
        {
            "_scraped_name": "2011 Special Session",
            "identifier": "2011_ss",
            "name": "2011 Special Session",
            "start_date": "2011-08-15",
            "end_date": "2011-08-15",
        },
        {
            "_scraped_name": "2013-2014 Regular Session",
            "identifier": "2013_14",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2014-03-21",
        },
        {
            "_scraped_name": "2015-2016 Regular Session",
            "identifier": "2015_16",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-12",
            "end_date": "2016-03-24",
        },
        {
            "_scraped_name": "2017-2018 Regular Session",
            "identifier": "2017_18",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2018-03-29",
        },
        {
            "_scraped_name": "2018 Special Session",
            "identifier": "2018_ss",
            "name": "2018 Special Session",
            "start_date": "2018-11-13",
            "end_date": "2018-11-17",
        },
        {
            "_scraped_name": "2020 Special Session",
            "identifier": "2020_ss",
            "name": "2020 Special Session",
            "start_date": "2020-03-16",
            "end_date": "2020-03-20",
        },
        {
            "_scraped_name": "2019-2020 Regular Session",
            "identifier": "2019_20",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2020-04-03",
        },
        {
            "_scraped_name": "2021-2022 Regular Session",
            "identifier": "2021_22",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-11",
            "end_date": "2022-04-02",
            "active": False,
        },
        {
            "_scraped_name": "2021 Special Session",
            "identifier": "2021_ss",
            "name": "2021 Special Session",
            "start_date": "2021-11-03",
            "end_date": "2021-11-22",
            "active": False,
        },
        {
            "_scraped_name": "2023-2024 Regular Session",
            "identifier": "2023_24",
            "name": "2023-2024 Regular Session",
            "start_date": "2023-01-09",
            "end_date": "2024-04-02",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "2009-2010 Regular Session",
        "2007-2008 Regular Session",
        "2005 Special Session",
        "2005-2006 Regular Session",
        "2004 Special Session",
        "2003-2004 Regular Session",
        "2001 2nd Special Session",
        "2001 1st Special Session",
        "2001-2002 Regular Session",
    ]

    def get_session_list(self):
        sessions = get_client("Session").service

        # sessions = [x for x in backoff(sessions.GetSessions)['Session']]
        # import pdb; pdb.set_trace()
        # sessions <-- check the Id for the _guid

        return [
            x["Description"].strip() for x in backoff(sessions.GetSessions)["Session"]
        ]
