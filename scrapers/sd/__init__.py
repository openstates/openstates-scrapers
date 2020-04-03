import scrapelib
import lxml.html
from .people import SDLegislatorScraper
from .bills import SDBillScraper
from scrapers.utils import State


class SouthDakota(State):
    scrapers = {"people": SDLegislatorScraper, "bills": SDBillScraper}
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
            "_scraped_name": "2011 Special",
            "identifier": "2011s",
            "name": "2011 Special Session",
            "start_date": "2011-10-24",
            "end_date": "2011-10-25",
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
            "_scraped_name": "2017 Special",
            "identifier": "2017s",
            "name": "2017 Special Session",
            "start_date": "2017-06-12",
            "end_date": "2017-06-12",
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-09",
            "end_date": "2018-03-26",
        },
        {
            "_scraped_name": "2018 Special",
            "identifier": "2018s",
            "name": "2018 Special Session",
            "start_date": "2018-09-12",
            "end_date": "2018-09-12",
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
    ]
    ignored_scraped_sessions = [
        "2008",
        "2007",
        "2006",
        "2005",
        "2005 Special",
        "2004",
        "2003",
        "2003 Special",
        "2002",
        "2001",
        "2001 Special",
        "2000",
        "2000 Special",
        "1999",
        "1998",
        "1997",
        "1997 Special",
    ]

    def get_session_list(self):
        html = (
            scrapelib.Scraper()
            .get("http://www.sdlegislature.gov/" "Legislative_Session/archive.aspx")
            .text
        )
        doc = lxml.html.fromstring(html)
        sessions = [
            x.strip() for x in doc.xpath('//table//td[@data-title="Year"]/text()')
        ]

        # Archive page lacks the latest session
        current_session_url = doc.xpath(
            '//*[@id="ctl00_divHeader_mnuMain"]/li[6]/ul/li[1]/a/@href'
        )[0]
        current_session = current_session_url.replace(
            "/Legislative_Session/Bills/Default.aspx?Session=", ""
        )
        if current_session not in sessions:
            sessions.append(current_session)

        return sessions
