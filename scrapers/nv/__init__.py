from utils import url_xpath
from openstates.scrape import State
from .bills import NVBillScraper
from .events import NVEventScraper


class Nevada(State):
    scrapers = {
        "bills": NVBillScraper,
        "events": NVEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "26th (2010) Special Session",
            "classification": "special",
            "identifier": "2010Special26",
            "name": "26th Special Session (2010)",
            "start_date": "2010-02-23",
            "end_date": "2010-03-01",
        },
        {
            "_scraped_name": "27th (2013) Special Session",
            "classification": "special",
            "identifier": "2013Special27",
            "name": "27th Special Session (2013)",
            "start_date": "2013-06-04",
            "end_date": "2013-06-04",
        },
        {
            "_scraped_name": "28th (2014) Special Session",
            "classification": "special",
            "identifier": "2014Special28",
            "name": "28th Special Session (2014)",
            "start_date": "2014-09-10",
            "end_date": "2014-09-11",
        },
        {
            "_scraped_name": "29th (2015) Special Session",
            "classification": "special",
            "identifier": "2015Special29",
            "name": "29th Special Session (2015)",
            "start_date": "2015-12-16",
            "end_date": "2015-12-19",
        },
        {
            "_scraped_name": "30th (2016) Special Session",
            "classification": "special",
            "identifier": "2016Special30",
            "name": "30th Special Session (2016)",
            "start_date": "2016-10-10",
            "end_date": "2016-10-14",
        },
        {
            "_scraped_name": "75th (2009) Session",
            "classification": "primary",
            "identifier": "75",
            "name": "2009 Regular Session",
            "start_date": "2009-02-02",
            "end_date": "2009-06-02",
        },
        {
            "_scraped_name": "76th (2011) Session",
            "classification": "primary",
            "identifier": "76",
            "name": "2011 Regular Session",
            "start_date": "2011-02-07",
            "end_date": "2011-06-06",
        },
        {
            "_scraped_name": "77th (2013) Session",
            "classification": "primary",
            "identifier": "77",
            "name": "2013 Regular Session",
            "start_date": "2013-02-04",
            "end_date": "2013-06-03",
        },
        {
            "_scraped_name": "78th (2015) Session",
            "classification": "primary",
            "identifier": "78",
            "name": "2015 Regular Session",
            "start_date": "2015-02-15",
            "end_date": "2015-06-01",
        },
        {
            "_scraped_name": "79th (2017) Session",
            "classification": "primary",
            "identifier": "79",
            "name": "2017 Regular Session",
            "start_date": "2017-02-06",
            "end_date": "2017-06-06",
        },
        {
            "_scraped_name": "80th (2019) Session",
            "classification": "primary",
            "identifier": "80",
            "name": "2019 Regular Session",
            "start_date": "2019-02-04",
            "end_date": "2019-06-03",
        },
        {
            "_scraped_name": "31st (2020) Special Session",
            "classification": "special",
            "identifier": "2020Special31",
            "name": "31st (2020) Special Session",
            "start_date": "2020-07-08",
            "end_date": "2020-07-19",
        },
        {
            "_scraped_name": "32nd (2020) Special Session",
            "classification": "special",
            "identifier": "2020Special32",
            "name": "32nd (2020) Special Session",
            "start_date": "2020-07-31",
            # TODO: correct end date after special completes
            "end_date": "2020-08-07",
        },
        {
            "_scraped_name": "81st (2021) Session",
            "classification": "primary",
            "identifier": "81",
            "name": "2021 Regular Session",
            "start_date": "2021-02-01",
            "end_date": "2021-06-01",
            "active": True,
        },
        {
            "_scraped_name": "33rd (2021) Special Session",
            "classification": "special",
            "identifier": "2021Special33",
            "name": "33rd (2021) Special Session",
            "start_date": "2021-11-12",
            "end_date": "2021-11-12",
        },
    ]
    ignored_scraped_sessions = [
        "25th (2008) Special Session",
        "24th (2008) Special Session",
        "23rd (2007) Special Session",
        "74th (2007) Session",
        "22nd (2005) Special Session",
        "73rd (2005) Session",
        "21st (2004) Special Session",
        "20th (2003) Special Session",
        "19th (2003) Special Session",
        "72nd (2003) Session",
        "18th (2002) Special Session",
        "17th (2001) Special Session",
        "71st (2001) Session",
        "70th (1999) Session",
        "69th (1997) Session",
        "68th (1995) Session",
        "67th (1993) Session",
        "66th (1991) Session",
        "16th (1989) Special Session",
        "65th (1989) Session",
        "64th (1987) Session",
        "63rd (1985) Session",
    ]

    def get_session_list(self):
        return url_xpath(
            "https://www.leg.state.nv.us/Session/",
            '//div[contains(@class, "list-group-item-heading")]/text()',
        )
