from pupa.scrape import Jurisdiction, Organization
from .people import NMPersonScraper


class NewMexico(Jurisdiction):
    division_id = "ocd-division/country:us/state:nm"
    classification = "government"
    name = "New Mexico"
    url = "TODO"
    scrapers = {
        'people': NMPersonScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular",
            "identifier": "2011",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2011 1st Special",
            "identifier": "2011S",
            "name": "2011 Special Session"
        },
        {
            "_scraped_name": "2012 Regular",
            "identifier": "2012",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "2013 Regular",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014 Regular",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2015 1st Special",
            "identifier": "2015S",
            "name": "2015 Special Session"
        },
        {
            "_scraped_name": "2016 Regular",
            "classification": "primary",
            "end_date": "2016-02-18",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-19"
        },
        {
            "_scraped_name": "2016 2nd Special",
            "classification": "special",
            "end_date": "2016-10-01",
            "identifier": "2016S",
            "name": "2016 2nd Special Session",
            "start_date": "2016-09-30"
        },
        {
            "_scraped_name": "2017 Regular",
            "classification": "primary",
            "end_date": "2017-03-18",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2016-01-17"
        }
    ]
    ignored_scraped_sessions = [
        "2010 2nd Special",
        "2010 Regular",
        "2009 1st Special",
        "2009 Regular",
        "2008 2nd Special",
        "2008 Regular",
        "2007 1st Special",
        "2007 Regular",
        "2006 Regular",
        "2005 1st Special",
        "2005 Regular",
        "2004 Regular",
        "2003 1st Special",
        "2003 Regular",
        "2002 Extraordinary",
        "2002 Regular",
        "2001 2nd Special",
        "2001 1st Special",
        "2001 Regular",
        "2000 2nd Special",
        "2000 Regular",
        "1999 1st Special",
        "1999 Regular",
        "1998 1st Special",
        "1998 Regular",
        "1997 Regular",
        "1996 1st Special",
        "1996 Regular"
    ]

    def get_organizations(self):
        legislature_name = "New Mexico Legislature"
        lower_chamber_name = "House"
        lower_seats = 70
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 42
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
