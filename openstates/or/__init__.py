from pupa.scrape import Jurisdiction, Organization
# from .people import ORPersonScraper
# from .committees import ORCommitteeScraper
from .bills import ORBillScraper
from .votes import ORVoteScraper


class Oregon(Jurisdiction):
    division_id = "ocd-division/country:us/state:or"
    classification = "government"
    name = "Oregon"
    url = "https://olis.leg.state.or.us"
    scrapers = {
        # 'people': ORPersonScraper,
        # 'committees': ORCommitteeScraper,
        'bills': ORBillScraper,
        'votes': ORVoteScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2007 Regular Session",
            "identifier": "2007 Regular Session",
            "name": "2007 Regular Session"
        },
        {
            "_scraped_name": "2008 Special Session",
            "identifier": "2008 Special Session",
            "name": "2008 Special Session"
        },
        {
            "_scraped_name": "2009 Regular Session",
            "identifier": "2009 Regular Session",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "2010 Special Session",
            "identifier": "2012 Special Session",
            "name": "2010 Special Session"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "identifier": "2011 Regular Session",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "identifier": "2012 Regular Session",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "2012 Special Session",
            "identifier": "2012 Special Session",
            "name": "2012 Speical Session"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2013 Special Session",
            "identifier": "2013 Special Session",
            "name": "2013 Special Session"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "identifier": "2014 Regular Session",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "identifier": "2016 Regular Session",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "end_date": "2017-07-10",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session",
            "start_date": "2017-02-01"
        },
        {
            "_scraped_name": "2018 Regular Session",
            "identifier": "2018 Regular Session",
            "name": "2018 Regular Session",
            "start_date": "2018-02-05",
            "end_date": "2018-03-09",
        },
        {
            "_scraped_name": "2018 1st Special Session",
            "identifier": "2018 Special Session",
            "name": "2018 Special Session",
            "start_date": "2018-05-21",
            "end_date": "2018-05-21",
        },
    ]
    ignored_scraped_sessions = [
        "Today",
        "2017-2018 Interim",
        "2015-2016 Interim",
        "2013 1st Special Session",
        "2012 1st Special Session",
        "2013 - 2014 Interim",
        "2011 - 2012 Interim",
        "2009 - 2010 Interim",
        "2007 - 2008 Interim"
    ]

    def get_organizations(self):
        legislature_name = "Oregon Legislative Assembly"
        lower_chamber_name = "House"
        lower_seats = 60
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 30
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        from .apiclient import OregonLegislatorODataClient
        sessions = OregonLegislatorODataClient(None).all_sessions()
        sessions = [s['SessionName'] for s in sessions]
        return sessions
