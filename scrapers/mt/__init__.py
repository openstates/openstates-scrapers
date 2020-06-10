from utils import url_xpath, State
from .people import MTPersonScraper
from .bills import MTBillScraper

# from .committees import MTCommitteeScraper


class Montana(State):
    scrapers = {
        "people": MTPersonScraper,
        # 'committees': MTCommitteeScraper,
        "bills": MTBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "20111",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-03",
            "end_date": "2011-04-28",
        },
        {
            "_scraped_name": "20131",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-07",
            "end_date": "2013-04-27",
        },
        {
            "_scraped_name": "20151",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-05",
            "end_date": "2015-04-28",
        },
        {
            "_scraped_name": "20171",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-02",
            "end_date": "2017-04-28",
        },
        {
            "_scraped_name": "20191",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-07",
            "end_date": "2019-04-25",
        },
        # TODO: Restore when they turn some LC's into bills
        # {
        #     "_scraped_name": "20211",
        #     "identifier": "2021",
        #     "name": "2021 Regular Session",
        #     "start_date": "2021-01-04",
        #     "end_date": "2021-04-25",
        # },        
    ]
    ignored_scraped_sessions = [
        "20211",
        "20172",
        "20091",
        "20072",
        "20071",
        "20052",
        "20051",
        "20031",
        "20011",
        "19991",
    ]

    def get_session_list(self):
        return url_xpath(
            "http://laws.leg.mt.gov/legprd/LAW0200W$.Startup",
            '//select[@name="P_SESS"]/option/@value',
        )
