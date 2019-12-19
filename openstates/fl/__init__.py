# encoding=utf-8
import logging
from pupa.scrape import Jurisdiction, Organization
from .bills import FlBillScraper
from .people import FlPersonScraper

# from .committees import FlCommitteeScraper
# from .events import FlEventScraper
from openstates.utils import url_xpath

logging.getLogger(__name__).addHandler(logging.NullHandler())


class Florida(Jurisdiction):
    division_id = "ocd-division/country:us/state:fl"
    classification = "government"
    name = "Florida"
    url = "http://myflorida.com"

    scrapers = {
        "bills": FlBillScraper,
        "people": FlPersonScraper,
        # "committees": FlCommitteeScraper,
        # "events": FlEventScraper,
    }
    legislative_sessions = [
        {
            "name": "2011 Regular Session",
            "identifier": "2011",
            "classification": "primary",
        },
        {
            "name": "2012 Regular Session",
            "identifier": "2012",
            "classification": "primary",
        },
        {
            "name": "2012 Extraordinary Apportionment Session",
            "identifier": "2012B",
            "classification": "special",
        },
        {
            "name": "2013 Regular Session",
            "identifier": "2013",
            "classification": "primary",
        },
        {
            "name": "2014 Regular Session",
            "identifier": "2014",
            "classification": "primary",
        },
        {
            "name": "2014 Special Session A",
            "identifier": "2014A",
            "classification": "special",
        },
        # data for the below
        {
            "name": "2015 Regular Session",
            "identifier": "2015",
            "classification": "primary",
        },
        {
            "name": "2015 Special Session A",
            "identifier": "2015A",
            "classification": "special",
        },
        {
            "name": "2015 Special Session B",
            "identifier": "2015B",
            "classification": "special",
        },
        {
            "name": "2015 Special Session C",
            "identifier": "2015C",
            "classification": "special",
        },
        {
            "name": "2016 Regular Session",
            "identifier": "2016",
            "classification": "primary",
        },
        {
            "name": "2017 Regular Session",
            "identifier": "2017",
            "classification": "primary",
            "start_date": "2017-03-07",
            "end_date": "2017-05-05",
        },
        {
            "name": "2017 Special Session A",
            "identifier": "2017A",
            "classification": "special",
        },
        {
            "name": "2018 Regular Session",
            "identifier": "2018",
            "classification": "primary",
            "start_date": "2018-01-08",
            "end_date": "2018-03-09",
        },
        {
            "name": "2019 Regular Session",
            "identifier": "2019",
            "classification": "primary",
            "start_date": "2019-03-05",
            "end_date": "2019-05-03",
        },
        {
            "name": "2020 Regular Session",
            "identifier": "2020",
            "classification": "primary",
            "start_date": "2020-01-14",
        },
    ]
    ignored_scraped_sessions = [
        *(str(each) for each in range(1997, 2010)),
        "2019 I",  # Empty, maybe informational session
        "2010",
        "2010A",
        "2010O",
        "2012O",
        "2014O",
        "2016O",
        "2018O",
        "2018 Org.",
        "2016 Org.",
        "2014 Org.",
        "2012 Org.",
        "2010 Org.",
        "2010C",
        "2009B",
        "2009A",
        "2008 Org.",
        "2007D",
        "2007C",
        "2007B",
        "2007A",
        "2006 Org.",
        "2005B",
        "2004A",
        "2004 Org.",
        "2003E",
        "2003D",
        "2003C",
        "2003B",
        "2003A",
        "2002E",
        "2002D",
        "2002 Org.",
        "2001C",
        "2001B",
        "2000A (Jan.)",
        "2000A (Dec.)",
        "2000 Org.",
        "1998 Org",
    ]

    def get_organizations(self):
        legis = Organization(name="Florida Legislature", classification="legislature")

        upper = Organization(
            "Florida Senate", classification="upper", parent_id=legis._id
        )
        lower = Organization(
            "Florida House of Representatives",
            classification="lower",
            parent_id=legis._id,
        )

        yield legis
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath("http://flsenate.gov", "//option/text()")
