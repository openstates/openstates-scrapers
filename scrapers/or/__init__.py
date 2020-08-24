from utils import State
from .people import ORPersonScraper
from .bills import ORBillScraper
from .votes import ORVoteScraper
from .events import OREventScraper

# from .committees import ORCommitteeScraper


class Oregon(State):
    scrapers = {
        "people": ORPersonScraper,
        # 'committees': ORCommitteeScraper,
        "bills": ORBillScraper,
        "votes": ORVoteScraper,
        "events": OREventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2007 Regular Session",
            "identifier": "2007 Regular Session",
            "name": "2007 Regular Session",
            "start_date": "2007-01-08",
            "end_date": "2007-06-28",
        },
        {
            "_scraped_name": "2008 Special Session",
            "identifier": "2008 Special Session",
            "name": "2008 Special Session",
            "start_date": "2008-02-04",
            "end_date": "2008-02-22",
        },
        {
            "_scraped_name": "2009 Regular Session",
            "identifier": "2009 Regular Session",
            "name": "2009 Regular Session",
            "start_date": "2009-01-12",
            "end_date": "2009-06-29",
        },
        {
            "_scraped_name": "2010 Special Session",
            "identifier": "2010 Special Session",
            "name": "2010 Special Session",
            "start_date": "2010-02-01",
            "end_date": "2010-02-25",
        },
        {
            "_scraped_name": "2011 Regular Session",
            "identifier": "2011 Regular Session",
            "name": "2011 Regular Session",
            "start_date": "2011-02-01",
            "end_date": "2011-06-30",
        },
        {
            "_scraped_name": "2012 Regular Session",
            "identifier": "2012 Regular Session",
            "name": "2012 Regular Session",
            "start_date": "2012-02-01",
            "end_date": "2012-03-05",
        },
        {
            "_scraped_name": "2012 Special Session",
            "identifier": "2012 Special Session",
            "name": "2012 Speical Session",
            "start_date": "2012-12-14",
            "end_date": "2012-12-14",
        },
        {
            "_scraped_name": "2013 Regular Session",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session",
            "start_date": "2013-02-04",
            "end_date": "2013-07-08",
        },
        {
            "_scraped_name": "2013 Special Session",
            "identifier": "2013 Special Session",
            "name": "2013 Special Session",
            "start_date": "2013-09-30",
            "end_date": "2013-10-02",
        },
        {
            "_scraped_name": "2014 Regular Session",
            "identifier": "2014 Regular Session",
            "name": "2014 Regular Session",
            "start_date": "2014-02-03",
            "end_date": "2014-03-07",
        },
        {
            "_scraped_name": "2015 Regular Session",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session",
            "start_date": "2015-02-02",
            "end_date": "2015-07-06",
        },
        {
            "_scraped_name": "2016 Regular Session",
            "identifier": "2016 Regular Session",
            "name": "2016 Regular Session",
            "start_date": "2016-02-01",
            "end_date": "2016-03-03",
        },
        {
            "_scraped_name": "2017 Regular Session",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session",
            "start_date": "2017-02-01",
            "end_date": "2017-07-07",
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
        {
            "_scraped_name": "2019 Regular Session",
            "identifier": "2019 Regular Session",
            "name": "2019 Regular Session",
            "start_date": "2019-01-22",
            "end_date": "2019-06-30",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "identifier": "2020 Regular Session",
            "name": "2020 Regular Session",
            "start_date": "2020-02-03",
            "end_date": "2020-03-08",
        },
        {
            "_scraped_name": "2020 1st Special Session",
            "identifier": "2020S1",
            "name": "2020 Special Session",
            "start_date": "2020-06-24",
            "end_date": "2020-07-03",
        },
        {
            "_scraped_name": "2020 2nd Special Session",
            "identifier": "2020S2",
            "name": "2020 Special Session 2",
            "start_date": "2020-08-10",
            # TODO: real end date when session ends
            "end_date": "2020-08-14",
        },
    ]
    ignored_scraped_sessions = [
        "Mock Session 2020",
        "Today",
        "2019-2020 Interim",
        "2017-2018 Interim",
        "2015-2016 Interim",
        "2013 1st Special Session",
        "2012 1st Special Session",
        "2013 - 2014 Interim",
        "2011 - 2012 Interim",
        "2009 - 2010 Interim",
        "2007 - 2008 Interim",
    ]

    def get_session_list(self):
        from .apiclient import OregonLegislatorODataClient

        sessions = OregonLegislatorODataClient(None).all_sessions()
        sessions = [s["SessionName"] for s in sessions]
        return sessions
