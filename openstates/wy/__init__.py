from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import WYBillScraper
from .people import WYPersonScraper
from .committees import WYCommitteeScraper


class Wyoming(Jurisdiction):
    division_id = "ocd-division/country:us/state:wy"
    classification = "government"
    name = "Wyoming"
    url = "http://legisweb.state.wy.us/"
    scrapers = {
        'bills': WYBillScraper,
        'people': WYPersonScraper,
        # 'committees': WYCommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011 General Session",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011 General Session"
        },
        {
            "_scraped_name": "2012 Budget Session",
            "classification": "special",
            "identifier": "2012",
            "name": "2012 Budget Session"
        },
        {
            "_scraped_name": "2013 General Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 General Session"
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
            "_scraped_name": "2016 General Session",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 General Session"
        },
        {
            "_scraped_name": "2017 General Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 General Session",
            "start_date": "2017-01-10",
            "end_date": "2017-03-03",
        }
    ]
    ignored_scraped_sessions = [
        "2016 Budget Session",
        "2014 Budget Session",
        "2010 Budget Session",
        "2009 General Session",
        "2008 Budget Session",
        "2007 General Session",
        "2006 Budget Session",
        "2005 General Session",
        "2004 Budget Session",
        "2003 General Session",
        "2002 Budget Session",
        "2001 General Session"
    ]

    def get_organizations(self):
        legislature_name = "Wyoming State Legislature"
        lower_chamber_name = "House"
        lower_seats = 60
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 30
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
        return url_xpath(
            'http://legisweb.state.wy.us/LSOWeb/SessionArchives.aspx',
            '//div[@id="divLegContent"]/a/p/text()',
        )
