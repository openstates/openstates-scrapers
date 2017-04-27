from .people import MDPersonScraper
from pupa.scrape import Jurisdiction, Organization


class Maryland(Jurisdiction):
    division_id = "ocd-division/country:us/state:md"
    classification = "government"
    name = "Maryland"
    url = "http://mgaleg.maryland.gov/webmga/frm1st.aspx?tab=home"
    scrapers = {
        'people': MDPersonScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2007 Regular Session",
            "classification": "primary",
            "end_date": "2007-04-10",
            "identifier": "2007",
            "name": "2007 Regular Session",
            "start_date": "2007-01-10"
        },
        {
            "_scraped_name": "2007 Special Session 1",
            "classification": "special",
            "end_date": "2007-11-19",
            "identifier": "2007s1",
            "name": "2007, 1st Special Session",
            "start_date": "2007-10-29"
        },
        {
            "_scraped_name": "2008 Regular Session",
            "classification": "primary",
            "end_date": "2008-04-07",
            "identifier": "2008",
            "name": "2008 Regular Session",
            "start_date": "2008-01-09"
        },
        {
            "_scraped_name": "2009 Regular Session",
            "classification": "primary",
            "end_date": "2009-04-13",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2009-01-14"
        },
        {
            "_scraped_name": "2010 Regular Session",
            "classification": "primary",
            "end_date": "2010-04-12",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-13"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2011-04-12",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-12"
        },
        {
            "_scraped_name": "2011 Special Session 1",
            "classification": "special",
            "identifier": "2011s1",
            "name": "2011, 1st Special Session"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "end_date": "2012-04-09",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11"
        },
        {
            "_scraped_name": "2012 Special Session 1",
            "classification": "special",
            "identifier": "2012s1",
            "name": "2012, 1st Special Session"
        },
        {
            "_scraped_name": "2012 Special Session 2",
            "classification": "special",
            "identifier": "2012s2",
            "name": "2012, 2nd Special Session"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2017-04-10",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11"
        }
    ]
    ignored_scraped_sessions = [
        "1996 Regular Session",
        "1997 Regular Session",
        "1998 Regular Session",
        "1999 Regular Session",
        "2000 Regular Session",
        "2001 Regular Session",
        "2002 Regular Session",
        "2003 Regular Session",
        "2004 Regular Session",
        "2004 Special Session 1",
        "2005 Regular Session",
        "2006 Regular Session",
        "2006 Special Session 1"
    ]

    def get_organizations(self):
        legislature_name = "Maryland General Assembly"
        lower_chamber_name = "House"
        lower_seats = 0 # was none
        lower_title = "Delegate"
        upper_chamber_name = "Senate"
        upper_seats = 0
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
