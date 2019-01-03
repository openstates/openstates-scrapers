from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath
from .people import VTPersonScraper
# from .committees import VTCommitteeScraper
from .bills import VTBillScraper
from .events import VTEventScraper


# As of March 2018, Vermont appears to be throttling hits
# to its website. After a week of production failures, we
# tried rate-limiting our requests, and the errors went away
# (Reminder: Pupa default is 60 RPM)
# This limit might also be possible to remove once we switch to
# the official API for bills:
# https://github.com/openstates/openstates/issues/2196
settings = dict(
    SCRAPELIB_RPM=20
)


class Vermont(Jurisdiction):
    division_id = "ocd-division/country:us/state:vt"
    classification = "government"
    name = "Vermont"
    url = "http://legislature.vermont.gov/"
    scrapers = {
        'people': VTPersonScraper,
        # 'committees': VTCommitteeScraper,
        'bills': VTBillScraper,
        'events': VTEventScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-2010 Session",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session"
        },
        {
            "_scraped_name": "2011-2012 Session",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-2014 Session",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016 Session",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018 Session",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2018-05-12",
        },
        {
            "_scraped_name": "2018 Special Session",
            "classification": "special",
            "identifier": "2018ss1",
            "name": "2018 Special Session",
            "start_date": "2018-05-22",
        },
        {
            "_scraped_name": "2019-2020 Session",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-09",
        },
    ]
    ignored_scraped_sessions = [
        "2020 Training Session",
        "2009 Special Session",
    ]

    site_ids = {
        '2018ss1': '2018.1',
    }

    def get_year_slug(self, session):
        return self.site_ids.get(session, session[5:])

    def get_organizations(self):
        legislature_name = "Vermont General Assembly"
        legislature = Organization(name=legislature_name, classification="legislature")
        governor = Organization(name='Office of the Governor', classification='executive')
        upper = Organization('Senate', classification='upper', parent_id=legislature._id)
        lower = Organization('House', classification='lower', parent_id=legislature._id)

        yield legislature
        yield governor
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
                'http://legislature.vermont.gov/bill/search/2016',
                '//fieldset/div[@id="selected_session"]/div/select/option/text()')
