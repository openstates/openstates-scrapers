from pupa.scrape import Jurisdiction, Organization
from openstates.utils.lxmlize import url_xpath
from .people import HIPersonScraper
# from .events import HIEventScraper
from .bills import HIBillScraper
# from .committees import HICommitteeScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class Hawaii(Jurisdiction):

    division_id = "ocd-division/country:us/state:hi"
    classification = "government"
    name = "Hawaii"
    url = "http://capitol.hawaii.gov"
    scrapers = {
        'people': HIPersonScraper,
        'bills': HIBillScraper,
        # 'committees': HICommitteeScraper,
        # 'events': HIEventScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2012",
            "identifier": "2011 Regular Session",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014",
            "identifier": "2014 Regular Session",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016",
            "identifier": "2016 Regular Session",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session",
            'start_date': '2017-01-18',
            'end_date': '2017-05-04'
        },
        {
            "_scraped_name": "2018",
            "identifier": "2018 Regular Session",
            "name": "2018 Regular Session",
            'start_date': '2018-01-18',
        },
        {
            "_scraped_name": "2019",
            "end_date": "2019-04-12",
            "identifier": "2019 Regular Session",
            "name": "2019 Regular Session",
            'start_date': '2019-01-15',
        }
    ]
    ignored_scraped_sessions = [
        "2011",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "2004",
        "2003",
        "2002",
        "2001",
        "2000",
        "1999"
    ]

    def get_organizations(self):
        legislature_name = "Hawaii State Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        # doesn't include current session, we need to change it
        sessions = url_xpath('http://www.capitol.hawaii.gov/archives/main.aspx',
                             "//div[@class='roundedrect gradientgray shadow']/a/text()"
                             )
        sessions.remove("Archives Main")
        return sessions
