import re
from utils import url_xpath
from openstates.scrape import State
from .bills import IABillScraper
from .votes import IAVoteScraper
from .events import IAEventScraper


class Iowa(State):
    scrapers = {
        "bills": IABillScraper,
        "votes": IAVoteScraper,
        "events": IAEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "General Assembly: 84",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-10",
            "end_date": "2012-05-09",
        },
        {
            "_scraped_name": "General Assembly: 85",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14",
            "end_date": "2014-05-02",
        },
        {
            "_scraped_name": "General Assembly: 86",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-12",
            "end_date": "2016-04-29",
        },
        {
            "_scraped_name": "General Assembly: 87",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09",
            "end_date": "2017-04-29",
        },
        {
            "_scraped_name": "General Assembly: 88",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2020-04-27",
        },
        {
            "_scraped_name": "General Assembly: 89",
            "classification": "primary",
            "identifier": "2021-2022",
            "name": "2021-2022 Regular Session",
            "start_date": "2021-01-11",
            "end_date": "2021-06-19",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "Legislative Assembly: 86",
        "General Assembly: 83",
        "General Assembly: 82",
        "General Assembly: 81",
        "General Assembly: 80",
        "General Assembly: 79",
        "General Assembly: 79",
        "General Assembly: 78",
        "General Assembly: 78",
        "General Assembly: 77",
        "General Assembly: 77",
        "General Assembly: 76",
    ]

    def get_session_list(self):
        sessions = url_xpath(
            "https://www.legis.iowa.gov/legislation/findLegislation",
            "//section[@class='grid_6']//li/a/text()[normalize-space()]",
        )

        return [
            x[0]
            for x in filter(
                lambda x: x != [],
                [re.findall(r"^.*Assembly: [0-9]+", session) for session in sessions],
            )
        ]
