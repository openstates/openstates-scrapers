import re

from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from .bills import CABillScraper

# from .events import CAEventScraper
from .people import CAPersonScraper

# from .committees import CACommitteeScraper


settings = dict(SCRAPELIB_RPM=30)


class California(Jurisdiction):
    division_id = "ocd-division/country:us/state:ca"
    classification = "government"
    name = "California"
    url = "http://www.legislature.ca.gov/"
    scrapers = {
        "bills": CABillScraper,
        # 'events': CAEventScraper,
        "people": CAPersonScraper,
        # 'committees': CACommitteeScraper,
    }
    legislative_sessions = [
        {
            "classification": "primary",
            "identifier": "19891990",
            "name": "1989-1990 Regular Session",
            "start_date": "1988-12-05",
        },
        {
            "classification": "primary",
            "identifier": "20032004",
            "name": "2003-2004 Regular Session",
            "start_date": "2002-12-02",
        },
        {
            "classification": "primary",
            "identifier": "20052006",
            "name": "2005-2006 Regular Session",
            "start_date": "2005-12-06",
        },
        {
            "classification": "primary",
            "identifier": "20072008",
            "name": "2007-2008 Regular Session",
            "start_date": "2006-12-04",
        },
        {
            "classification": "primary",
            "identifier": "20092010",
            "name": "2009-2010 Regular Session",
            "start_date": "2008-12-01",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 1",
            "name": "2009-2010, 1st Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 2",
            "name": "2009-2010, 2nd Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 3",
            "name": "2009-2010, 3rd Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 4",
            "name": "2009-2010, 4th Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 5",
            "name": "2009-2010, 5th Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 6",
            "name": "2009-2010, 6th Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 7",
            "name": "2009-2010, 7th Special Session",
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 8",
            "name": "2009-2010, 8th Special Session",
        },
        {
            "classification": "primary",
            "identifier": "20112012",
            "name": "2011-2012 Regular Session",
            "start_date": "2010-12-06",
        },
        {
            "classification": "special",
            "identifier": "20112012 Special Session 1",
            "name": "2011-2012, 1st Special Session",
        },
        {
            "classification": "primary",
            "identifier": "20132014",
            "name": "2013-2014 Regular Session",
        },
        {
            "classification": "special",
            "identifier": "20132014 Special Session 1",
            "name": "2013-2014, 1st Special Session",
        },
        {
            "classification": "special",
            "identifier": "20132014 Special Session 2",
            "name": "2013-2014, 2nd Special Session",
        },
        {
            "_scraped_name": "2015-2016",
            "classification": "primary",
            "identifier": "20152016",
            "name": "2015-2016 Regular Session",
        },
        {
            "classification": "special",
            "identifier": "20152016 Special Session 1",
            "name": "2015-2016, 1st Special Session",
        },
        {
            "classification": "special",
            "identifier": "20152016 Special Session 2",
            "name": "2015-2016, 2nd Special Session",
        },
        {
            "_scraped_name": "2017-2018",
            "classification": "primary",
            "end_date": "2017-09-15",
            "identifier": "20172018",
            "name": "2017-2018 Regular Session",
            "start_date": "2016-12-05",
        },
        {
            "_scraped_name": "2019-2020",
            "classification": "primary",
            "identifier": "20192020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-02",
            "end_date": "2020-12-31",
        },
    ]
    ignored_scraped_sessions = [
        "2013-2014",
        "2011-2012",
        "2009-2010",
        "2007-2008",
        "2005-2006",
        "2003-2004",
        "2001-2002",
        "1999-2000",
        "1997-1998",
        "1995-1996",
        "1993-1994",
    ]

    def get_organizations(self):
        legislature_name = "California State Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization(
            "Assembly", classification="lower", parent_id=legislature._id
        )

        yield Organization(name="Office of the Governor", classification="executive")
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
            "http://www.leginfo.ca.gov/bilinfo.html",
            "//select[@name='sess']/option/text()",
        )
        return [re.findall(r"\(.*\)", session)[0][1:-1] for session in sessions]
