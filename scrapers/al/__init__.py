from utils import State
from .bills import ALBillScraper
from .events import ALEventScraper


class Alabama(State):
    scrapers = {
        "bills": ALBillScraper,
        "events": ALEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "Regular Session 2011",
            "classification": "primary",
            "identifier": "2011rs",
            "name": "2011 Regular Session",
            "start_date": "2011-03-01",
            "end_date": "2011-06-09",
        },
        {
            "_scraped_name": "First Special Session 2012",
            "classification": "special",
            "identifier": "2012fs",
            "name": "First Special Session 2012",
            "start_date": "2012-05-17",
            "end_date": "2012-05-24",
        },
        {
            "_scraped_name": "Regular Session 2012",
            "classification": "primary",
            "identifier": "2012rs",
            "name": "2012 Regular Session",
            "start_date": "2012-02-07",
            "end_date": "2012-05-16",
        },
        {
            "_scraped_name": "Regular Session 2013",
            "classification": "primary",
            "identifier": "2013rs",
            "name": "2013 Regular Session",
            "start_date": "2013-02-05",
            "end_date": "2013-05-20",
        },
        {
            "_scraped_name": "Regular Session 2014",
            "classification": "primary",
            "identifier": "2014rs",
            "name": "2014 Regular Session",
            "start_date": "2014-01-14",
            "end_date": "2014-04-04",
        },
        {
            "_scraped_name": "First Special Session 2015",
            "classification": "special",
            "identifier": "2015fs",
            "name": "First Special Session 2015",
            "start_date": "2015-07-13",
            "end_date": "2015-08-11",
        },
        {
            "_scraped_name": "Organizational Session 2015",
            "classification": "primary",
            "identifier": "2015os",
            "name": "2015 Organizational Session",
            "start_date": "2015-01-13",
            "end_date": "2015-01-14",
        },
        {
            "_scraped_name": "Regular Session 2015",
            "classification": "primary",
            "identifier": "2015rs",
            "name": "2015 Regular Session",
            "start_date": "2015-03-03",
            "end_date": "2015-06-04",
        },
        {
            "_scraped_name": "Second Special Session 2015",
            "classification": "special",
            "identifier": "2015ss",
            "name": "Second Special Session 2015",
            "start_date": "2015-09-08",
            "end_date": "2015-09-16",
        },
        {
            "_scraped_name": "First Special Session 2016",
            "classification": "special",
            "identifier": "2016fs",
            "name": "First Special Session 2016",
            "start_date": "2016-08-15",
            "end_date": "2016-09-07",
        },
        {
            "_scraped_name": "Regular Session 2016",
            "classification": "primary",
            "identifier": "2016rs",
            "name": "2016 Regular Session",
            "start_date": "2016-02-02",
            "end_date": "2016-05-04",
        },
        {
            "_scraped_name": "Regular Session 2017",
            "classification": "primary",
            "end_date": "2017-05-31",
            "identifier": "2017rs",
            "name": "2017 Regular Session",
            "start_date": "2017-02-07",
        },
        {
            "_scraped_name": "Regular Session 2018",
            "classification": "primary",
            "end_date": "2018-03-29",
            "identifier": "2018rs",
            "name": "2018 Regular Session",
            "start_date": "2018-01-09",
        },
        {
            "_scraped_name": "First Special Session 2019",
            "classification": "special",
            "identifier": "2019fs",
            "name": "First Special Session 2019",
            "start_date": "2019-03-08",
            "end_date": "2019-03-12",
        },
        {
            "_scraped_name": "Regular Session 2019",
            "classification": "primary",
            "end_date": "2019-06-17",
            "identifier": "2019rs",
            "name": "2019 Regular Session",
            "start_date": "2019-03-05",
        },
        {
            "_scraped_name": "Regular Session 2020",
            "classification": "primary",
            "identifier": "2020rs",
            "name": "2020 Regular Session",
            "start_date": "2020-02-04",
            "end_date": "2020-05-18",
        },
        {
            "_scraped_name": "Regular Session 2021",
            "classification": "primary",
            "identifier": "2021rs",
            "name": "2021 Regular Session",
            "start_date": "2021-02-02",
            "end_date": "2021-05-18",
        },
        {
            "_scraped_name": "Regular Session 2022",
            "classification": "primary",
            "identifier": "2022rs",
            "name": "2022 Regular Session",
            "start_date": "2022-01-11",
            # TODO: Real end date after session
            "end_date": "2022-05-18",
        },
        {
            "_scraped_name": "First Special Session 2021",
            "classification": "special",
            "identifier": "2021s1",
            "name": "First Special Session 2021",
            "start_date": "2021-09-27",
            "end_date": "2021-10-01",
        },
    ]
    ignored_scraped_sessions = [
        # TODO: add to scraped when prefiles up
        "Second Special Session 2021",
        "Regular Session 1998",
        "Organizational Session 1999",
        "Regular Session 1999",
        "First Special Session 1999",
        "Organizational Session 2011",
        "Second Special Session 1999",
        "Regular Session 2000",
        "Regular Session 2001",
        "First Special Session 2001",
        "Second Special Session 2001",
        "Third Special Session 2001",
        "Fourth Special Session 2001",
        "Regular Session 2002",
        "Organizational Session 2003",
        "Regular Session 2003",
        "First Special Session 2003",
        "Second Special Session 2003",
        "Regular Session 2004",
        "First Special Session 2004",
        "Regular Session 2005",
        "First Special Session 2005",
        "Regular Session 2006",
        "Organizational Session 2007",
        "Regular Session 2007",
        "First Special Session 2007",
        "Regular Session 2008",
        "First Special Session 2008",
        "Regular Session 2009",
        "Regular Session 2010",
        "First Special Session 2009",
        "First Special Session 2010",
        "Regular Session 2016",
        "Organizational Session 2019",
    ]

    def get_session_list(self):
        import lxml.html
        import requests

        s = requests.Session()
        r = s.get("http://alisondb.legislature.state.al.us/alison/SelectSession.aspx")
        doc = lxml.html.fromstring(r.text)
        return doc.xpath(
            '//*[@id="ContentPlaceHolder1_gvSessions"]/tr/td/font/a/font/text()'
        )
