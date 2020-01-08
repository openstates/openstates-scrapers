from pupa.scrape import Jurisdiction, Organization

from .people import WVPersonScraper

# from .committees import WVCommitteeScraper
from .bills import WVBillScraper


class WestVirginia(Jurisdiction):
    division_id = "ocd-division/country:us/state:wv"
    classification = "government"
    name = "West Virginia"
    url = "http://www.legis.state.wv.us/"
    scrapers = {
        "people": WVPersonScraper,
        # 'committees': WVCommitteeScraper,
        "bills": WVBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011 Regular Session",
        },
        {
            "_scraped_name": "2012",
            "classification": "primary",
            "identifier": "2012",
            "name": "2012 Regular Session",
        },
        {
            "_scraped_name": "2013",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 Regular Session",
        },
        {
            "_scraped_name": "2014",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 Regular Session",
        },
        {
            "_scraped_name": "2015",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 Regular Session",
        },
        {
            "_scraped_name": "2016",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session",
        },
        {
            "_scraped_name": "2016",
            "classification": "special",
            "identifier": "20161S",
            "name": "2016 First Special Session",
        },
        {
            "_scraped_name": "2017",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-02-08",
            "end_date": "2017-04-09",
        },
        {
            "_scraped_name": "2017",
            "classification": "special",
            "identifier": "20171S",
            "name": "2017 First Special Session",
            "start_date": "2017-05-04",
            "end_date": "2017-06-26",
        },
        {
            "_scraped_name": "2017",
            "classification": "special",
            "identifier": "20172S",
            "name": "2017 Second Special Session",
            "start_date": "2017-10-16",
            "end_date": "2017-10-17",
        },
        {
            "_scraped_name": "2018",
            "classification": "primary",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-10",
        },
        {
            "_scraped_name": "2018",
            "classification": "special",
            "identifier": "20181S",
            "name": "2018 First Special Session",
            "start_date": "2018-05-20",
            "end_date": "2018-05-25",
        },
        {
            "_scraped_name": "2018",
            "classification": "special",
            "identifier": "20182S",
            "name": "2018 Second Special Session",
            "start_date": "2018-08-12",
        },
        {
            "_scraped_name": "2019",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2019-03-09",
        },
        {
            "_scraped_name": "2019",
            "classification": "special",
            "identifier": "20191S",
            "name": "2019 First Special Session",
            "start_date": "2019-05-20",
        },
        {
            "_scraped_name": "2020",
            "classification": "primary",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
            "end_date": "2020-03-07",
        },
    ]
    ignored_scraped_sessions = [
        "2020",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "2004",
        "2003",
        "2002",
        "2001",
        "2000",
        "1999",
        "1998",
        "1997",
        "1996",
        "1995",
        "1994",
        "1993",
    ]

    def get_organizations(self):
        legislature_name = "West Virginia Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization("House", classification="lower", parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        from openstates.utils import url_xpath

        return url_xpath(
            "http://www.legis.state.wv.us/Bill_Status/Bill_Status.cfm",
            '//select[@name="year"]/option/text()',
        )
