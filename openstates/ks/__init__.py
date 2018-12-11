from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from openstates.ks.bills import KSBillScraper
# from openstates.ks.people import KSPersonScraper
# from openstates.ks.committees import KSCommitteeScraper


# Kansas API's 429 error response includes:
# You have received this notification because this IP address is querying
# the kslegislature.org website at a high rate. If the queries are generated
# by an automated tool, please introduce a delay rate of 3-5 seconds between queries.
settings = dict(
    SCRAPELIB_TIMEOUT=300,
    SCRAPELIB_RPM=12
)


class Kansas(Jurisdiction):
    division_id = "ocd-division/country:us/state:ks"
    classification = "government"
    name = "Kansas"
    url = "http://www.kslegislature.org/"
    scrapers = {
        'bills': KSBillScraper,
        # 'people': KSPersonScraper,
        # 'committees': KSCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "b2011_12",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-12"
        },
        {
            "_scraped_name": "b2013_14",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-14"
        },
        {
            "_scraped_name": "b2015_16",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2013-01-14"
        },
        {
            "_scraped_name": "b2017_18",
            "classification": "primary",
            "end_date": "2017-05-19",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-09"
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "Kansas State Legislature"
        upper_chamber_name = "Senate"
        lower_seats = 125
        lower_title = "Representative"
        lower_chamber_name = "House"
        upper_seats = 40
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
        url = url_xpath(
            'http://www.kslegislature.org/li',
            '//div[@id="nav"]//a[contains(text(), "Senate Bills")]/@href',
        )[0]
        return [url.split('/')[2]]
