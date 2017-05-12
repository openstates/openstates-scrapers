import re

from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from .bills import CABillScraper
from .events import CAEventScraper
from .people import CAPersonScraper
from .committees import CACommitteeScraper


settings = dict(SCRAPELIB_RPM=30)


class California(Jurisdiction):
    division_id = "ocd-division/country:us/state:ca"
    classification = "government"
    name = "California"
    url = "http://www.legislature.ca.gov/"
    scrapers = {
        'bills': CABillScraper,
        'events': CAEventScraper,
        'people': CAPersonScraper,
        'committees': CACommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "classification": "primary",
            "identifier": "20092010",
            "name": "2009-2010 Regular Session",
            "start_date": "2008-12-01"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 1",
            "name": "2009-2010, 1st Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 2",
            "name": "2009-2010, 2nd Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 3",
            "name": "2009-2010, 3rd Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 4",
            "name": "2009-2010, 4th Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 5",
            "name": "2009-2010, 5th Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 6",
            "name": "2009-2010, 6th Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 7",
            "name": "2009-2010, 7th Special Session"
        },
        {
            "classification": "special",
            "identifier": "20092010 Special Session 8",
            "name": "2009-2010, 8th Special Session"
        },
        {
            "classification": "primary",
            "identifier": "20112012",
            "name": "2011-2012 Regular Session",
            "start_date": "2010-12-06"
        },
        {
            "classification": "special",
            "identifier": "20112012 Special Session 1",
            "name": "2011-2012, 1st Special Session"
        },
        {
            "classification": "primary",
            "identifier": "20132014",
            "name": "2013-2014 Regular Session"
        },
        {
            "classification": "special",
            "identifier": "20132014 Special Session 1",
            "name": "2013-2014, 1st Special Session"
        },
        {
            "classification": "special",
            "identifier": "20132014 Special Session 2",
            "name": "2013-2014, 2nd Special Session"
        },
        {
            "_scraped_name": "2015-2016",
            "classification": "primary",
            "identifier": "20152016",
            "name": "2015-2016 Regular Session"
        },
        {
            "classification": "special",
            "identifier": "20152016 Special Session 1",
            "name": "2015-2016, 1st Special Session"
        },
        {
            "classification": "special",
            "identifier": "20152016 Special Session 2",
            "name": "2015-2016, 2nd Special Session"
        },
        {
            "_scraped_name": "2017-2018",
            "classification": "primary",
            "end_date": "2017-09-15",
            "identifier": "20172018",
            "name": "2017-2018 Regular Session",
            "start_date": "2016-12-05"
        }
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
        "1993-1994"
    ]

    def get_organizations(self):
        legislature_name = "California State Legislature"
        lower_chamber_name = "Assembly"
        lower_seats = 80
        lower_title = "Assemblymember"
        upper_chamber_name = "Senate"
        upper_seats = 40
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
            'http://www.leginfo.ca.gov/bilinfo.html',
            "//select[@name='sess']/option/text()")
        return [
            re.findall('\(.*\)', session)[0][1:-1]
            for session in sessions
        ]
