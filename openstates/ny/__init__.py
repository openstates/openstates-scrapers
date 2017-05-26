from .committees import NYCommitteeScraper
from pupa.scrape import Jurisdiction, Organization
from .people import NYPersonScraper
from openstates.utils import url_xpath


class NewYork(Jurisdiction):
    division_id = "ocd-division/country:us/state:ny"
    classification = "government"
    name = "New York"
    url = "TODO"
    scrapers = {
        'people': NYPersonScraper,
        'committees': NYCommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009",
            "identifier": "2009-2010",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "2011",
            "identifier": "2011-2012",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013-2014",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2015",
            "identifier": "2015-2016",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2017",
            "identifier": "2017-2018",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2009"
    ]

    def get_organizations(self):
        legislature_name = "New York Legislature"
        lower_chamber_name = "Assembly"
        lower_seats = 150
        lower_title = "Assembly Member"
        upper_chamber_name = "Senate"
        upper_seats = 63
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

    def get_session_list(self):
        url = 'http://nysenate.gov/search/legislation'
        sessions = url_xpath(url,
            '//select[@name="bill_session_year"]/option[@value!=""]/@value')
        return sessions
