# from .people import DEPersonScraper
from .bills import DEBillScraper
# from .events import DEEventScraper
# from .committees import DECommitteeScraper

from openstates.utils import url_xpath

from pupa.scrape import Jurisdiction, Organization


class Delaware(Jurisdiction):
    division_id = "ocd-division/country:us/state:de"
    classification = "government"
    name = "Delaware"
    url = "http://legis.delaware.gov/"
    scrapers = {
        # 'people': DEPersonScraper,
        'bills': DEBillScraper,
        # 'events': DEEventScraper,
        # 'committees': DECommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "1998 - 2000 (GA 140)",
            "identifier": "140",
            "name": "140th General Assembly (1999-2000)"
        },
        {
            "_scraped_name": "2000 - 2002 (GA 141)",
            "identifier": "141",
            "name": "141st General Assembly (2001-2002)"
        },
        {
            "_scraped_name": "2002 - 2004 (GA 142)",
            "identifier": "142",
            "name": "142nd General Assembly (2003-2004)"
        },
        {
            "_scraped_name": "2004 - 2006 (GA 143)",
            "identifier": "143",
            "name": "143rd General Assembly (2005-2006)"
        },
        {
            "_scraped_name": "2006 - 2008 (GA 144)",
            "identifier": "144",
            "name": "144th General Assembly (2007-2008)"
        },
        {
            "_scraped_name": "2008 - 2010 (GA 145)",
            "identifier": "145",
            "name": "145th General Assembly (2009-2010)"
        },
        {
            "_scraped_name": "2010 - 2012 (GA 146)",
            "identifier": "146",
            "name": "146th General Assembly (2011-2012)"
        },
        {
            "_scraped_name": "2012 - 2014 (GA 147)",
            "identifier": "147",
            "name": "147th General Assembly (2013-2014)"
        },
        {
            "_scraped_name": "2014 - 2016 (GA 148)",
            "identifier": "148",
            "name": "148th General Assembly (2015-2016)"
        },
        {
            "_scraped_name": "2016 - 2018 (GA 149)",
            "identifier": "149",
            "name": "149th General Assembly (2017-2018)",
            "start_date": "2017-01-10",
            "end_date": "2017-06-30"
        },
        # TODO: uncomment when they start posting
        # {
        #     "_scraped_name": "2018 - 2020 (GA 150)",
        #     "identifier": "150",
        #     "name": "150th General Assembly (2019-2020)",
        #     "start_date": "2019-01-08",
        #     "end_date": "2019-06-27"
        # }
    ]
    ignored_scraped_sessions = ['2018 - 2020 (GA 150)']

    def get_organizations(self):
        legislature_name = "Delaware General Assembly"
        lower_chamber_name = "House"
        upper_chamber_name = "Senate"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name="Office of the Governor",
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
        url = 'https://legis.delaware.gov/'
        sessions = url_xpath(url, '//select[@id="billSearchGARefiner"]/option/text()')
        sessions = [session.strip() for session in sessions if session.strip()]
        return sessions
