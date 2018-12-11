from pupa.scrape import Jurisdiction, Organization

from .util import get_client, backoff
from .bills import GABillScraper
# from .people import GAPersonScraper
# from .committees import GACommitteeScraper


class Georgia(Jurisdiction):
    division_id = "ocd-division/country:us/state:ga"
    classification = "government"
    name = "Georgia"
    url = "http://www.legis.ga.gov/"
    scrapers = {
        'bills': GABillScraper,
        # 'people': GAPersonScraper,
        # 'committee': GACommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011-2012 Regular Session",
            "identifier": "2011_12",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2011 Special Session",
            "identifier": "2011_ss",
            "name": "2011 Special Session"
        },
        {
            "_scraped_name": "2013-2014 Regular Session",
            "identifier": "2013_14",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016 Regular Session",
            "identifier": "2015_16",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018 Regular Session",
            "identifier": "2017_18",
            "name": "2017-2018 Regular Session",
            'start_date': '2017-01-09',
            'end_date': '2017-03-31'
        },
        {
            "_scraped_name": "2018 Special Session",
            "identifier": "2018_ss",
            "name": "2018 Special Session",
            'start_date': '2018-11-13',
            'end_date': '2018-11-17',
        },
        {
            "_scraped_name": "2019-2020 Regular Session",
            "identifier": "2019_20",
            "name": "2019-2020 Regular Session",
            'start_date': '2019-01-14',
            'end_date': '2020-03-31'
        },
    ]
    ignored_scraped_sessions = [
        "2009-2010 Regular Session",
        "2007-2008 Regular Session",
        "2005 Special Session",
        "2005-2006 Regular Session",
        "2004 Special Session",
        "2003-2004 Regular Session",
        "2001 2nd Special Session",
        "2001 1st Special Session",
        "2001-2002 Regular Session"
    ]

    def get_organizations(self):
        legislature_name = "Georgia General Assembly"
        lower_chamber_name = "House"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = get_client("Session").service

        # sessions = [x for x in backoff(sessions.GetSessions)['Session']]
        # import pdb; pdb.set_trace()
        # sessions <-- check the Id for the _guid

        return [x['Description'].strip()
                for x in backoff(sessions.GetSessions)['Session']]
