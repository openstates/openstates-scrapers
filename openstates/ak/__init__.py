from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import AKBillScraper
# from .events import AKEventScraper
# from .people import AKPersonScraper
# from .committees import AKCommitteeScraper

settings = dict(SCRAPELIB_TIMEOUT=600)


class Alaska(Jurisdiction):
    division_id = "ocd-division/country:us/state:ak"
    classification = "government"
    name = "Alaska"
    url = "http://w3.legis.state.ak.us/"
    scrapers = {
        'bills': AKBillScraper,
        # 'events': AKEventScraper,
        # 'people': AKPersonScraper,
        # 'committees': AKCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "The 27th Legislature (2011-2012)",
            "identifier": "27",
            "name": "27th Legislature (2011-2012)"
        },
        {
            "_scraped_name": "The 28th Legislature (2013-2014)",
            "identifier": "28",
            "name": "28th Legislature (2013-2014)"
        },
        {
            "_scraped_name": "The 29th Legislature (2015-2016)",
            "identifier": "29",
            "name": "29th Legislature (2015-2016)"
        },
        {
            "_scraped_name": "The 30th Legislature (2017-2018)",
            "end_date": "2017-04-16",
            "identifier": "30",
            "name": "30th Legislature (2017-2018)",
            "start_date": "2017-01-17"
        }
    ]
    ignored_scraped_sessions = [
        "The 26th Legislature (2009-2010)",
        "The 25th Legislature (2007-2008)",
        "The 24th Legislature (2005-2006)",
        "The 23rd Legislature (2003-2004)",
        "The 22nd Legislature (2001-2002)",
        "The 21st Legislature (1999-2000)",
        "The 20th Legislature (1997-1998)",
        "The 19th Legislature (1995-1996)",
        "The 18th Legislature (1993-1994)"
    ]

    def get_organizations(self):
        legislature_name = "Alaska State Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization("Senate", classification='upper', parent_id=legislature._id)
        lower = Organization("House", classification='lower', parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'http://www.legis.state.ak.us/basis/start.asp',
            "//div[@id='rightnav']//a[contains(@href, 'start.asp?session=')]//nobr/text()"
        )
