from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from .bills import TXBillScraper
# from .committees import TXCommitteeScraper
from .events import TXEventScraper
from .people import TXPersonScraper
from .votes import TXVoteScraper


class Texas(Jurisdiction):
    division_id = "ocd-division/country:us/state:tx"
    classification = "government"
    name = "Texas"
    url = "https://capitol.texas.gov/"
    scrapers = {
        'people': TXPersonScraper,
        # 'committees': TXCommitteeScraper,
        'bills': TXBillScraper,
        # Re-enable vote scraper when adding next regular session
        'votes': TXVoteScraper,
        'events': TXEventScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "81(R) - 2009",
            "classification": "primary",
            "end_date": "2009-06-01",
            "identifier": "81",
            "name": "81st Legislature (2009)",
            "start_date": "2009-01-13"
        },
        {
            "_scraped_name": "81(1) - 2009",
            "classification": "special",
            "end_date": "2009-07-02",
            "identifier": "811",
            "name": "81st Legislature, 1st Called Session (2009)",
            "start_date": "2009-07-01"
        },
        {
            "_scraped_name": "82(R) - 2011",
            "classification": "primary",
            "end_date": "2011-05-30",
            "identifier": "82",
            "name": "82nd Legislature (2011)",
            "start_date": "2011-01-11"
        },
        {
            "_scraped_name": "82(1) - 2011",
            "classification": "special",
            "end_date": "2011-06-29",
            "identifier": "821",
            "name": "82nd Legislature, 1st Called Session (2011)",
            "start_date": "2011-05-31"
        },
        {
            "_scraped_name": "83(R) - 2013",
            "classification": "primary",
            "end_date": "2013-05-27",
            "identifier": "83",
            "name": "83rd Legislature (2013)",
            "start_date": "2013-01-08"
        },
        {
            "_scraped_name": "83(1) - 2013",
            "classification": "special",
            "end_date": "2013-06-25",
            "identifier": "831",
            "name": "83nd Legislature, 1st Called Session (2013)",
            "start_date": "2013-05-27"
        },
        {
            "_scraped_name": "83(2) - 2013",
            "classification": "special",
            "end_date": "2013-07-30",
            "identifier": "832",
            "name": "83nd Legislature, 2st Called Session (2013)",
            "start_date": "2013-07-01"
        },
        {
            "_scraped_name": "83(3) - 2013",
            "classification": "special",
            "end_date": "2013-08-05",
            "identifier": "833",
            "name": "83nd Legislature, 3rd Called Session (2013)",
            "start_date": "2013-07-30"
        },
        {
            "_scraped_name": "84(R) - 2015",
            "classification": "primary",
            "end_date": "2015-06-01",
            "identifier": "84",
            "name": "84th Legislature (2015)",
            "start_date": "2015-01-13"
        },
        {
            "_scraped_name": "85(R) - 2017",
            "classification": "primary",
            "end_date": "2017-06-01",
            "identifier": "85",
            "name": "85th Legislature (2017)",
            "start_date": "2017-01-13"
        },
        {
            "_scraped_name": "85(1) - 2017",
            "classification": "special",
            "end_date": "2017-08-19",
            "identifier": "851",
            "name": "85nd Legislature, 1st Called Session (2017)",
            "start_date": "2017-07-10"
        },
        {
            "_scraped_name": "86(R) - 2019",
            "classification": "primary",
            "end_date": "2019-05-27",
            "identifier": "86",
            "name": "86th Legislature (2019)",
            "start_date": "2019-01-08"
        },
        # TODO: Re-enable vote scraper when adding next regular session
    ]
    ignored_scraped_sessions = [
        "80(R) - 2007",
        "79(3) - 2006",
        "79(2) - 2005",
        "79(1) - 2005",
        "79(R) - 2005",
        "78(4) - 2004",
        "78(3) - 2003",
        "78(2) - 2003",
        "78(1) - 2003",
        "78(R) - 2003",
        "77(R) - 2001",
        "76(R) - 1999",
        "75(R) - 1997",
        "74(R) - 1995",
        "73(R) - 1993",
        "72(4) - 1992",
        "72(3) - 1992",
        "72(2) - 1991",
        "72(1) - 1991",
        "72(R) - 1991",
        "71(6) - 1990",
        "71(5) - 1990",
        "71(4) - 1990",
        "71(3) - 1990",
        "71(2) - 1989",
        "71(1) - 1989",
        "71(R) - 1989"
    ]

    def get_session_list(self):
        return url_xpath('https://capitol.texas.gov/',
                         '//select[@name="cboLegSess"]/option/text()')

    def get_organizations(self):
        legislature_name = "Texas Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower
