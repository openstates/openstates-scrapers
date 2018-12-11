import re

from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

# from .people import UTPersonScraper
from .events import UTEventScraper
# from .committees import UTCommitteeScraper
from .bills import UTBillScraper


class Utah(Jurisdiction):
    division_id = "ocd-division/country:us/state:ut"
    classification = "government"
    name = "Utah"
    url = "http://le.utah.gov/"
    scrapers = {
        # 'people': UTPersonScraper,
        'events': UTEventScraper,
        # 'committees': UTCommitteeScraper,
        'bills': UTBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 General Session",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-24"
        },
        {
            "_scraped_name": "2011 1st Special Session",
            "classification": "special",
            "identifier": "2011S1",
            "name": "2011, 1st Special Session"
        },
        {
            "_scraped_name": "2011 2nd Special Session",
            "classification": "special",
            "identifier": "2011S2",
            "name": "2011, 2nd Special Session"
        },
        {
            "_scraped_name": "2011 3rd Special Session",
            "classification": "special",
            "identifier": "2011S3",
            "name": "2011, 3rd Special Session"
        },
        {
            "_scraped_name": "2012 General Session",
            "classification": "primary",
            "identifier": "2012",
            "name": "2012 General Session"
        },
        {
            "_scraped_name": "2012 4th Special Session",
            "classification": "special",
            "identifier": "2012S4",
            "name": "2012, 4th Special Session"
        },
        {
            "_scraped_name": "2013 General Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 General Session"
        },
        {
            "_scraped_name": "2013 House Session",
            "classification": "special",
            "identifier": "2013h1",
            "name": "2013 House Session"
        },
        {
            "_scraped_name": "2013 1st Special Session",
            "classification": "special",
            "identifier": "2013s1",
            "name": "2013 1st Special Session"
        },
        {
            "_scraped_name": "2013 2nd Special Session",
            "classification": "special",
            "identifier": "2013s2",
            "name": "2013 2nd Special Session"
        },
        {
            "_scraped_name": "2014 General Session",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 General Session"
        },
        {
            "_scraped_name": "2015 General Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 General Session"
        },
        {
            "_scraped_name": "2015 1st Special Session",
            "classification": "special",
            "identifier": "2015s1",
            "name": "2015 1st Special Session"
        },
        {
            "_scraped_name": "2016 General Session",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 General Session",
            "start_date": "2016-01-25"
        },
        {
            "_scraped_name": "2016 2nd Special Session",
            "classification": "special",
            "identifier": "2016S2",
            "name": "2016 2nd Special Session",
            "start_date": "2016-05-18"
        },
        {
            "_scraped_name": "2016 3rd Special Session",
            "classification": "special",
            "identifier": "2016S3",
            "name": "2016 3rd Special Session",
            "start_date": "2016-07-13"
        },
        {
            "_scraped_name": "2016 4th Special Session",
            "classification": "special",
            "identifier": "2016S4",
            "name": "2016 4th Special Session",
            "start_date": "2016-11-16"
        },
        {
            "_scraped_name": "2017 General Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 General Session",
            "start_date": "2017-01-23",
            "end_date": "2017-03-09",
        },
        {
            "_scraped_name": "2017 1st Special Session",
            "classification": "special",
            "identifier": "2017S1",
            "name": "2017 1st Special Session",
            "start_date": "2017-09-20",
            "end_date": "2017-09-20",
        },
        {
            "_scraped_name": "2018 General Session",
            "classification": "primary",
            "identifier": "2018",
            "name": "2018 General Session",
            "start_date": "2018-01-22",
            "end_date": "2018-03-08",
        },
        {
            "_scraped_name": "2018 2nd Special Session",
            "classification": "special",
            "identifier": "2018S2",
            "name": "2017 2nd Special Session",
            "start_date": "2018-07-18",
        },
        {
            "_scraped_name": "2018 3rd Special Session",
            "classification": "special",
            "identifier": "2018S3",
            "name": "2017 3rd Special Session",
            "start_date": "2018-12-03",
        },
    ]
    ignored_scraped_sessions = [
        "2011 Veto Override Session",
        "2010 2nd Special Session",
        "2010 General Session",
        "2009 1st Special Session",
        "2009 General Session",
        "2008 2nd Special Session",
        "2008 General Session",
        "2007 1st Special Session",
        "2007 General Session",
        "2006 5th Special Session",
        "2006 4th Special Session",
        "2006 3rd Special Session",
        "2006 General Session",
        "2005 2nd Special Session",
        "2005 1st Special Session",
        "2005 General Session",
        "2004 4th Special Session",
        "2004 3rd Special Session",
        "2004 General Session",
        "2003 2nd Special Session",
        "2003 1st Special Session",
        "2003 General Session",
        "2002 Veto Override Session",
        "2002 6th Special Session",
        "2002 5th Special Session",
        "2002 4th Special Session",
        "2002 3rd Special Session",
        "2002 General Session",
        "2001 2nd Special Session",
        "2001 1st Special Session",
        "2001 General Session",
        "2000 General Session",
        "1999 General Session",
        "1998 General Session",
        "1997 2nd Special Session",
        "1997 1st Special Session",
        "1997 General Session",
        "1990-1996"
    ]

    def get_organizations(self):
        legislature_name = "Utah State Legislature"
        lower_chamber_name = "House"
        lower_seats = 75
        lower_title = "Senator"
        upper_chamber_name = "Senate"
        upper_seats = 29
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        # fiscal analyst
        # fisc = Organization('Office of the Legislative Fiscal Analyst',
        #                     classification='department',
        #                     parent_id=legislature._id,
        #                     )

        yield legislature
        yield Organization('Office of the Governor', classification='executive')
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
                'http://le.utah.gov/Documents/bills.htm',
                '//p/a[contains(@href, "session")]/text()'
                )
        return [re.sub(r'\s+', ' ', session.strip()) for session in sessions]
