from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from .bills import NJBillScraper
from .events import NJEventScraper
# from .people import NJPersonScraper
# from .committees import NJCommitteeScraper

# don't retry- if a file isn't on FTP just let it go
settings = dict(SCRAPELIB_RETRY_ATTEMPTS=0)


class NewJersey(Jurisdiction):
    division_id = "ocd-division/country:us/state:nj"
    classification = "government"
    name = "New Jersey"
    url = "http://www.njleg.state.nj.us/"
    scrapers = {
        'bills': NJBillScraper,
        'events': NJEventScraper,
        # 'people': NJPersonScraper,
        # 'committees': NJCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2008-2009",
            "identifier": "213",
            "name": "2008-2009 Regular Session",
            "start_date": "2008-01-12"
        },
        {
            "_scraped_name": "2010-2011",
            "identifier": "214",
            "name": "2010-2011 Regular Session",
            "start_date": "2010-01-12"
        },
        {
            "_scraped_name": "2012-2013",
            "identifier": "215",
            "name": "2012-2013 Regular Session",
            "start_date": "2012-01-10"
        },
        {
            "_scraped_name": "2014-2015",
            "identifier": "216",
            "name": "2014-2015 Regular Session",
            "start_date": "2014-01-15"
        },
        {
            "_scraped_name": "2016-2017",
            "identifier": "217",
            "name": "2016-2017 Regular Session",
            "start_date": "2016-01-12",
            "end_date": "2018-01-09"
        },
        {
            "_scraped_name": "2018-2019",
            "identifier": "218",
            "name": "2018-2019 Regular Session",
            "start_date": "2018-01-08",
            "end_date": "2020-01-09"
        },
    ]
    ignored_scraped_sessions = [
        "2006-2007",
        "2004-2005",
        "2002-2003",
        "2000-2001",
        "1998-1999",
        "1996-1997"
    ]

    def get_organizations(self):
        legislature_name = "New Jersey Legislature"
        lower_chamber_name = "Assembly"
        lower_seats = 40
        lower_title = "Assembly Member"
        upper_chamber_name = "Senate"
        upper_seats = 40
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name='Governor of New Jersey',
                                 classification="executive")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('http://www.njleg.state.nj.us/',
                         '//select[@name="DBNAME"]/option/text()')
