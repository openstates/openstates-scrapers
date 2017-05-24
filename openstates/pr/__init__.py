from pupa.scrape import Jurisdiction, Organization
from .people import PRPersonScraper
from .events import PREventScraper
from .committees import PRCommitteeScraper
from .bills import PRBillScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class PuertoRico(Jurisdiction):
    division_id = "ocd-division/country:us/state:pr"
    classification = "government"
    name = "Puerto Rico"
    url = "http://www.oslpr.org/"
    scrapers = {
        'people': PRPersonScraper,
        'events': PREventScraper,
        'committees': PRCommitteeScraper,
        'bills': PRBillScraper,
    }
    parties = [
        {'name': 'Partido Nuevo Progresista'},
        {'name': u'Partido Popular Democr\xe1tico'},
        {'name': u'Partido Independentista Puertorrique\u00F1o'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009-2012",
            "identifier": "2009-2012",
            "name": "2009-2012 Session"
        },
        {
            "_scraped_name": "2013-2016",
            "identifier": "2013-2016",
            "name": "2013-2016 Session"
        },
        {
            "_scraped_name": "2017-2020",
            "identifier": "2017-2020",
            "name": "2017-2020 Session"
        }
    ]
    ignored_scraped_sessions = [
        "2005-2008",
        "2001-2004",
        "1997-2000",
        "1993-1996"
    ]

    def get_organizations(self):
        legislature_name = "Legislative Assembly of Puerto Rico"
        lower_chamber_name = "House"
        lower_seats = None
        lower_title = "Senator"
        upper_chamber_name = "Senate"
        upper_seats = 0
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
        from openstates.utils import url_xpath
        # this URL should work even for future sessions
        return url_xpath('http://www.oslpr.org/legislatura/tl2013/buscar_2013.asp',
                         '//select[@name="URL"]/option/text()')
