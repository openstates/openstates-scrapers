import json
import requests

from .bills import SDBillScraper
from .events import SDEventScraper
from openstates.scrape import State


class SouthDakota(State):
    scrapers = {
        "bills": SDBillScraper,
        "events": SDEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2009-01-13",
            "end_date": "2009-03-30",
        },
        {
            "_scraped_name": "2010",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-12",
            "end_date": "2010-03-29",
        },
        {
            "_scraped_name": "2011",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-11",
            "end_date": "2011-03-28",
        },
        {
            "_scraped_name": "2011s",
            "identifier": "2011s",
            "name": "2011 Special Session",
            "start_date": "2011-10-24",
            "end_date": "2011-10-25",
            "classification": "special",
        },
        {
            "_scraped_name": "2012",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-10",
            "end_date": "2012-03-19",
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-08",
            "end_date": "2013-03-25",
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-14",
            "end_date": "2014-03-31",
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-13",
            "end_date": "2015-03-30",
        },
        {
            "_scraped_name": "2016",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-12",
            "end_date": "2016-03-29",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-10",
            "end_date": "2017-03-27",
        },
        {
            "_scraped_name": "2017s",
            "identifier": "2017s",
            "name": "2017 Special Session",
            "start_date": "2017-06-12",
            "end_date": "2017-06-12",
            "classification": "special",
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-09",
            "end_date": "2018-03-26",
        },
        {
            "_scraped_name": "2018s",
            "identifier": "2018s",
            "name": "2018 Special Session",
            "start_date": "2018-09-12",
            "end_date": "2018-09-12",
            "classification": "special",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-08",
            "end_date": "2019-03-13",
        },
        {
            "_scraped_name": "2020",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-14",
            "end_date": "2020-03-30",
        },
        {
            "_scraped_name": "2020s",
            "identifier": "2020s",
            "name": "2020 Special Session",
            "start_date": "2020-10-05",
            "end_date": "2020-10-05",
            "classification": "special",
        },
        {
            "_scraped_name": "2021",
            "identifier": "2021",
            "name": "2021 Regular Session",
            "start_date": "2021-01-12",
            "end_date": "2021-03-29",
            "active": True,
        },
        {
            "_scraped_name": "2021r",
            "identifier": "2021r",
            "name": "2021 Special Session",
            "start_date": "2021-11-08",
            "end_date": "2021-11-12",
            "classification": "special",
            "active": True,
        },
        {
            "_scraped_name": "2021i",
            "identifier": "2021i",
            "name": "2021 Second Special Session",
            "start_date": "2021-11-08",
            "end_date": "2021-11-12",
            "classification": "special",
            "active": True,
        },
    ]
    ignored_scraped_sessions = ["2022"]

    def get_session_list(self):
        api_url = "https://sdlegislature.gov/api/Sessions/"
        data = json.loads(requests.get(api_url).content)

        sessions = []
        for row in data:
            if int(row["Year"][0:4]) > 2008:
                sessions.append(row["Year"].strip())

        return sessions
