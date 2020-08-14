import lxml.html
import scrapelib
from utils import State
from .people import CTPersonScraper
from .bills import CTBillScraper
from .events import CTEventScraper

settings = {"SCRAPELIB_RPM": 20}

SKIP_SESSIONS = {"incoming", "pub", "CGAAudio", "rba", "NCSL", "FOI_1", "stainedglass"}


class Connecticut(State):
    scrapers = {
        "people": CTPersonScraper,
        "bills": CTBillScraper,
        "events": CTEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05",
            "end_date": "2011-06-08"
        },
        {
            "_scraped_name": "2012",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-02-08",
            "end_date": "2012-05-09"
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2013-06-05"
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-02-05",
            "end_date": "2014-05-07"
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2015-06-03"
        },
        {
            "_scraped_name": "2016",
            "end_date": "2016-05-04",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-02-03",
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2017-06-07",
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-02-07",
            "end_date": "2018-05-09",
        },
        {
            "_scraped_name": "2019",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2019-06-05",
        },
        {
            "_scraped_name": "2020",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-02-05",
            "end_date": "2020-05-06",
        },
    ]
    ignored_scraped_sessions = [
        "test.txt",
        "20xx",
        "2021",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "default",
        "Committees_Jud_related",
    ]

    def get_session_list(self):
        text = scrapelib.Scraper().get("ftp://ftp.cga.ct.gov").text
        sessions = [line.split()[-1] for line in text.splitlines()]
        return [session for session in sessions if session not in SKIP_SESSIONS]

    def get_extract_text(self, doc, data):
        doc = lxml.html.fromstring(data)
        text = " ".join(p.text_content() for p in doc.xpath("//body/p"))
        return text
