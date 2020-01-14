import re

from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .people import KYPersonScraper

# from .committees import KYCommitteeScraper
from .bills import KYBillScraper


class Kentucky(Jurisdiction):
    division_id = "ocd-division/country:us/state:ky"
    classification = "government"
    name = "Kentucky"
    url = "http://www.lrc.ky.gov/"
    scrapers = {
        "people": KYPersonScraper,
        # 'committees': KYCommitteeScraper,
        "bills": KYBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2011-03-09",
            "identifier": "2011 Regular Session",
            "name": "2011 Regular Session",
            "start_date": "2011-01-04",
        },
        {
            "_scraped_name": "2011 Special Session",
            "classification": "special",
            "end_date": "2011-04-06",
            "identifier": "2011SS",
            "name": "2011 Extraordinary Session",
            "start_date": "2011-03-14",
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "end_date": "2012-04-12",
            "identifier": "2012RS",
            "name": "2012 Regular Session",
            "start_date": "2012-01-03",
        },
        {
            "_scraped_name": "2012 Special Session",
            "classification": "special",
            "end_date": "2012-04-20",
            "identifier": "2012SS",
            "name": "2012 Extraordinary Session",
            "start_date": "2012-04-16",
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "end_date": "2013-03-26",
            "identifier": "2013RS",
            "name": "2013 Regular Session",
            "start_date": "2013-01-08",
        },
        {
            "_scraped_name": "2013 Special Session",
            "classification": "special",
            "end_date": "2013-08-19",
            "identifier": "2013SS",
            "name": "2013 Extraordinary Session",
            "start_date": "2013-08-19",
        },
        {
            "_scraped_name": "2014 Regular Session",
            "classification": "primary",
            "end_date": "2014-04-15",
            "identifier": "2014RS",
            "name": "2014 Regular Session",
            "start_date": "2014-01-07",
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "end_date": "2015-03-25",
            "identifier": "2015RS",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06",
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "end_date": "2016-04-12",
            "identifier": "2016RS",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05",
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2017-03-30",
            "identifier": "2017RS",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03",
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "end_date": "2018-04-13",
            "identifier": "2018RS",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02",
        },
        {
            "_scraped_name": "2018 Special Session",
            "classification": "special",
            "end_date": "2018-12-18",
            "identifier": "2018SS",
            "name": "2018 Special Session",
            "start_date": "2018-12-19",
        },
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019RS",
            "name": "2019 Regular Session",
            "start_date": "2019-01-08",
        },
        {
            "_scraped_name": "2019 Special Session",
            "classification": "special",
            "identifier": "2019SS",
            "name": "2019 Special Session",
            "start_date": "2019-07-19",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "classification": "primary",
            "identifier": "2020RS",
            "name": "2020 Regular Session",
            "start_date": "2020-01-07",
            "end_date": "2020-04-15",
        },
    ]
    ignored_scraped_sessions = [
        "2020 Regualr Session Prefiled",
        "2019 Regular Session Prefiled Bills",
        "2011 Special Session",
        "2011 Regular Session",
        "2010 Special Session",
        "2010 Regular Session",
        "2009 Special Session",
        "2009 Regular Session",
        "2008 Special Session",
        "2008 Regular Session",
        "2007 2nd Special Session",
        "2007 Special Session",
        "2007 Regular Session",
        "2006 Special Session",
        "2006 Regular Session",
        "2005 Regular Session",
        "2004 Special Session",
        "2004 Regular Session",
        "2003 Regular Session",
        "2002 Special Session",
        "2002 Regular Session",
        "2001 Regular Session",
        "2000 Regular Session",
        "1998 Regular Session",
        "1997 Special Session (Sept)",
        "1997 Special Session (May)",
    ]

    def get_organizations(self):
        legislature_name = "Kentucky General Assembly"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization("House", classification="lower", parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
            "https://apps.legislature.ky.gov/record/pastses.html", "//td/div/a/text()"
        )

        for index, session in enumerate(sessions):
            # Remove escaped whitespace characters.
            sessions[index] = re.sub(r"\s\s+", " ", session)
            sessions[index] = sessions[index].strip()

        return sessions
