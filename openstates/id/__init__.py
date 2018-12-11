from pupa.scrape import Jurisdiction, Organization
# from .people import IDPersonScraper
# from .committees import IDCommitteeScraper
from .bills import IDBillScraper
from openstates.utils.lxmlize import url_xpath


class Idaho(Jurisdiction):
    division_id = "ocd-division/country:us/state:id"
    classification = "government"
    name = "Idaho"
    url = "http://www.legislature.idaho.gov"
    scrapers = {
        # 'people': IDPersonScraper,
        # 'committees': IDCommitteeScraper,
        'bills': IDBillScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Session",
            "classification": "primary",
            "end_date": "2011-04-07",
            "identifier": "2011",
            "name": "61st Legislature, 1st Regular Session (2011)",
            "start_date": "2011-01-10"
        },
        {
            "_scraped_name": "2012 Session",
            "classification": "primary",
            "identifier": "2012",
            "name": "61st Legislature, 2nd Regular Session (2012)"
        },
        {
            "_scraped_name": "2013 Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "62nd Legislature, 1st Regular Session (2013)"
        },
        {
            "_scraped_name": "2014 Session",
            "classification": "primary",
            "identifier": "2014",
            "name": "63nd Legislature, 1st Regular Session (2014)"
        },
        {
            "_scraped_name": "2015 Session",
            "classification": "primary",
            "end_date": "2015-04-10",
            "identifier": "2015",
            "name": "64th Legislature, 1st Regular Session (2015)",
            "start_date": "2015-01-12"
        },
        {
            "_scraped_name": "2015 Extraordinary Session",
            "classification": "special",
            "end_date": "2015-05-18",
            "identifier": "2015spcl",
            "name": "65th Legislature, 1st Extraordinary Session (2015)",
            "start_date": "2015-05-18"
        },
        {
            "_scraped_name": "2016 Session",
            "classification": "primary",
            "end_date": "2016-03-25",
            "identifier": "2016",
            "name": "63rd Legislature, 2nd Regular Session (2016)",
            "start_date": "2016-01-11"
        },
        {
            "_scraped_name": "2017 Session",
            "classification": "primary",
            "end_date": "2017-04-07",
            "identifier": "2017",
            "name": "64th Legislature, 1st Regular Session (2017)",
            "start_date": "2017-01-09"
        },
        {
            "_scraped_name": "2018 Session",
            "classification": "primary",
            "end_date": "2018-03-27",
            "identifier": "2018",
            "name": "64th Legislature, 2nd Regular Session (2018)",
            "start_date": "2018-01-08"
        }
    ]
    ignored_scraped_sessions = [
        "2010 Session",
        "2009 Session",
        "2008 Session",
        "2007 Session",
        "2006 Extraordinary Session",
        "2006 Session",
        "2005 Session",
        "2004 Session",
        "2003 Session",
        "2002 Session",
        "2001 Session",
        "2000 Extraordinary Session",
        "2000 Session",
        "1999 Session",
        "1998 Session"
    ]

    def get_organizations(self):
        legislature_name = "Idaho State Legislature"
        lower_chamber_name = "House"
        lower_seats = 35
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 35
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('https://legislature.idaho.gov/sessioninfo/',
                         '//select[@id="ddlsessions"]/option/text()')
