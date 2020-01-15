# encoding=utf-8
from openstates.utils import url_xpath
from pupa.scrape import Jurisdiction, Organization
from .bills import IlBillScraper
from .people import IlPersonScraper
from .events import IlEventScraper

# from .committees import IlCommitteeScraper


class Illinois(Jurisdiction):
    division_id = "ocd-division/country:us/state:il"
    classification = "government"
    name = "Illinois"
    url = "http://www.ilga.gov/"
    scrapers = {
        "bills": IlBillScraper,
        "people": IlPersonScraper,
        "events": IlEventScraper,
        # "committees": IlCommitteeScraper,
    }
    legislative_sessions = [
        {
            "name": "90th Regular Session",
            "identifier": "90th",
            "classification": "primary",
            "_scraped_name": "90   (1997-1998)",
        },
        {
            "name": "91st Regular Session",
            "identifier": "91st",
            "classification": "primary",
            "_scraped_name": "91   (1999-2000)",
        },
        {
            "name": "92nd Regular Session",
            "identifier": "92nd",
            "classification": "primary",
            "_scraped_name": "92   (2001-2002)",
        },
        {
            "name": "93rd Regular Session",
            "identifier": "93rd",
            "classification": "primary",
            "_scraped_name": "93   (2003-2004)",
        },
        {
            "name": "93rd Special Session",
            "identifier": "93rd-special",
            "classification": "special",
        },
        {
            "name": "94th Regular Session",
            "identifier": "94th",
            "classification": "primary",
            "_scraped_name": "94   (2005-2006)",
        },
        {
            "name": "95th Regular Session",
            "identifier": "95th",
            "classification": "primary",
            "_scraped_name": "95   (2007-2008)",
        },
        {
            "name": "95th Special Session",
            "identifier": "95th-special",
            "classification": "special",
        },
        {
            "name": "96th Regular Session",
            "identifier": "96th",
            "classification": "primary",
            "_scraped_name": "96   (2009-2010)",
        },
        {
            "name": "96th Special Session",
            "identifier": "96th-special",
            "classification": "special",
        },
        {
            "name": "97th Regular Session",
            "identifier": "97th",
            "classification": "primary",
            "_scraped_name": "97   (2011-2012)",
        },
        {
            "name": "98th Regular Session",
            "identifier": "98th",
            "classification": "primary",
            "_scraped_name": "98   (2013-2014)",
        },
        {
            "name": "99th Regular Session",
            "identifier": "99th",
            "classification": "primary",
            "_scraped_name": "99   (2015-2016)",
        },
        {
            "name": "100th Special Session",
            "identifier": "100th-special",
            "classification": "special",
            "_scraped_name": "100   (2017-2018)",
        },
        {
            "name": "100th Regular Session",
            "identifier": "100th",
            "classification": "primary",
        },
        {
            "name": "101st Regular Session",
            "identifier": "101st",
            "start_date": "2019-01-09",
            "end_date": "2019-12-31",
            "classification": "primary",
        },
    ]

    ignored_scraped_sessions = [
        "77   (1971-1972)",
        "78   (1973-1974)",
        "79   (1975-1976)",
        "80   (1977-1978)",
        "81   (1979-1980)",
        "82   (1981-1982)",
        "83   (1983-1984)",
        "84   (1985-1986)",
        "85   (1987-1988)",
        "86   (1989-1990)",
        "87   (1991-1992)",
        "88   (1993-1994)",
        "89   (1995-1996)",
        "90   (1997-1998)",
        "91   (1999-2000)",
        "92   (2001-2002)",
    ]

    def get_organizations(self):
        legis = Organization(
            name="Illinois General Assembly", classification="legislature"
        )

        upper = Organization(
            "Illinois Senate", classification="upper", parent_id=legis._id
        )
        lower = Organization(
            "Illinois House of Representatives",
            classification="lower",
            parent_id=legis._id,
        )

        yield legis
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath("http://ilga.gov/PreviousGA.asp", "//option/text()")
