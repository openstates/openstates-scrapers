import re
from openstates.utils import url_xpath

from pupa.scrape import Jurisdiction, Organization
from .people import COLegislatorScraper

# from .committees import COCommitteeScraper
from .bills import COBillScraper
from .events import COEventScraper


class Colorado(Jurisdiction):
    division_id = "ocd-division/country:us/state:co"
    classification = "government"
    name = "Colorado"
    url = "http://leg.colorado.gov/"
    scrapers = {
        "people": COLegislatorScraper,
        # 'committees': COCommitteeScraper,
        "bills": COBillScraper,
        "events": COEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "identifier": "2011A",
            "name": "2011 Regular Session",
            "start_date": "2011-01-26",
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "identifier": "2012A",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11",
        },
        {
            "_scraped_name": "2012 First Extraordinary Session",
            "classification": "special",
            "identifier": "2012B",
            "name": "2012 First Extraordinary Session",
            "start_date": "2012-05-14",
        },
        {
            "_scraped_name": "2013 Regular/Special Session",
            "classification": "primary",
            "identifier": "2013A",
            "name": "2013 Regular Session",
        },
        {
            "_scraped_name": "2014 Legislative Session",
            "classification": "primary",
            "identifier": "2014A",
            "name": "2014 Regular Session",
        },
        {
            "_scraped_name": "2015 Legislative Session",
            "classification": "primary",
            "identifier": "2015A",
            "name": "2015 Regular Session",
        },
        {
            "_scraped_name": "2016 Legislative Session",
            "classification": "primary",
            "identifier": "2016A",
            "name": "2016 Regular Session",
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "identifier": "2017A",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-05-10",
        },
        {
            "_scraped_name": "8017 First Extraordinary Session",
            "classification": "special",
            "identifier": "2017B",
            "name": "2017 First Extraordinary Session",
            "start_date": "2017-10-02",
            "end_date": "2017-10-06",
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "identifier": "2018A",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-11",
        },
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019A",
            "name": "2019 Regular Session",
            "start_date": "2019-01-04",
            "end_date": "2019-05-03",
        },
    ]
    ignored_scraped_sessions = [
        "2013 Legislative Session",
        "2012 First Special Session",
        "2012 Legislative Session",
        "2011 Legislative Session",
        "2010 Legislative Session",
        "2009 Legislative Session",
        "2008 Legislative Session",
        "2007 Legislative Session",
        "2006 First Special Session",
        "2006 Legislative Session",
        "2005 Legislative Session",
        "2004 Legislative Session",
        "2003 Legislative Session",
        "2002 First Special Session",
        "2002 Legislative Session",
        "2001 Second Special Session",
        "2001 First Special Session",
        "2001 Legislative Session",
        "2000 Legislative Session",
        "2010 Regular/Special Session",
    ]

    def get_organizations(self):
        legislature_name = "Colorado General Assembly"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization("House", classification="lower", parent_id=legislature._id)
        executive = Organization("Office of the Governor", classification="executive")

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        sessions = []
        regex = r"2[0-9][0-9][0-9]\ .*\ Session"

        tags = url_xpath(
            "http://www.leg.state.co.us/clics/cslFrontPages.nsf/PrevSessionInfo?OpenForm",
            "//font/text()",
        )
        for tag in tags:
            sess = re.findall(regex, tag)
            for session in sess:
                sessions.append(session)

        return sessions
