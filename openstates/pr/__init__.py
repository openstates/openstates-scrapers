from pupa.scrape import Jurisdiction, Organization
# from .people import PRPersonScraper
# from .committees import PRCommitteeScraper
from .bills import PRBillScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class PuertoRico(Jurisdiction):
    division_id = "ocd-division/country:us/territory:pr"
    classification = "government"
    name = "Puerto Rico"
    url = "http://www.oslpr.org/"
    scrapers = {
        # 'people': PRPersonScraper,
        # 'committees': PRCommitteeScraper,
        'bills': PRBillScraper,
    }
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
            "name": "2017-2020 Session",
            "start_date": "2017-01-02",
            "end_date": "2021-01-01",
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
        lower_title = "Senator"
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        # 8 districts w/ 2 members, + 11 at larg
        for i, d in enumerate(('I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII')):
            upper.add_post(label=d, role=upper_title,
                           division_id='{}/sldu:{}'.format(self.division_id, i + 1))
        upper.add_post(label='At-Large', role=upper_title,
                       division_id='{}/sldu:at-large'.format(self.division_id))

        # lower house is 40 seats, + 11 at large
        for n in range(1, 41):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))
        lower.add_post(label='At-Large', role=lower_title,
                       division_id='{}/sldl:at-large'.format(self.division_id))

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        from openstates.utils import url_xpath
        # this URL should work even for future sessions
        return url_xpath('http://www.oslpr.org/legislatura/tl2013/buscar_2013.asp',
                         '//select[@name="URL"]/option/text()')
