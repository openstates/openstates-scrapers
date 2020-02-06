from openstates.utils import State
from .people import PRPersonScraper
from .bills import PRBillScraper

# from .committees import PRCommitteeScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class PuertoRico(State):
    scrapers = {
        "people": PRPersonScraper,
        # 'committees': PRCommitteeScraper,
        "bills": PRBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-2012",
            "identifier": "2009-2012",
            "name": "2009-2012 Session",
        },
        {
            "_scraped_name": "2013-2016",
            "identifier": "2013-2016",
            "name": "2013-2016 Session",
        },
        {
            "_scraped_name": "2017-2020",
            "identifier": "2017-2020",
            "name": "2017-2020 Session",
            "start_date": "2017-01-02",
            "end_date": "2021-01-01",
        },
    ]
    ignored_scraped_sessions = ["2005-2008", "2001-2004", "1997-2000", "1993-1996"]

    def get_session_list(self):
        from openstates.utils import url_xpath

        # this URL should work even for future sessions
        return url_xpath(
            "http://www.oslpr.org/legislatura/tl2013/buscar_2013.asp",
            '//select[@name="URL"]/option/text()',
        )
