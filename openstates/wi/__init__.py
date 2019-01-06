from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import WIBillScraper
# from .events import WIEventScraper
from .people import WIPersonScraper
# from .committees import WICommitteeScraper


class Wisconsin(Jurisdiction):
    division_id = "ocd-division/country:us/state:wi"
    classification = "government"
    name = "Wisconsin"
    url = "http://legis.wisconsin.gov/"
    scrapers = {
        'bills': WIBillScraper,
        # 'events': WIEventScraper,
        'people': WIPersonScraper,
        # 'committees': WICommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009 Regular Session",
            "classification": "primary",
            "end_date": "2011-01-03",
            "identifier": "2009 Regular Session",
            "name": "2009 Regular Session",
            "start_date": "2009-01-13"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2013-01-07",
            "identifier": "2011 Regular Session",
            "name": "2011 Regular Session",
            "start_date": "2011-01-11"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "end_date": "2014-01-13",
            "identifier": "2013 Regular Session",
            "name": "2013 Regular Session",
            "start_date": "2013-01-07"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "end_date": "2016-01-11",
            "identifier": "2015 Regular Session",
            "name": "2015 Regular Session",
            "start_date": "2015-01-05"
        },
        {
            "_scraped_name": "December 2009 Special Session",
            "classification": "special",
            "identifier": "December 2009 Special Session",
            "name": "Dec 2009 Special Session"
        },
        {
            "_scraped_name": "December 2013 Special Session",
            "classification": "special",
            "identifier": "December 2013 Special Session",
            "name": "Dec 2013 Special Session"
        },
        {
            "_scraped_name": "January 2011 Special Session",
            "classification": "special",
            "identifier": "January 2011 Special Session",
            "name": "Jan 2011 Special Session"
        },
        {
            "_scraped_name": "January 2014 Special Session",
            "classification": "special",
            "identifier": "January 2014 Special Session",
            "name": "Jan 2014 Special Session"
        },
        {
            "_scraped_name": "June 2009 Special Session",
            "classification": "special",
            "identifier": "June 2009 Special Session",
            "name": "Jun 2009 Special Session"
        },
        {
            "_scraped_name": "October 2013 Special Session",
            "classification": "special",
            "identifier": "October 2013 Special Session",
            "name": "Oct 2013 Special Session"
        },
        {
            "_scraped_name": "September 2011 Special Session",
            "classification": "special",
            "identifier": "September 2011 Special Session",
            "name": "Sep 2011 Special Session"
        },
        {
            'identifier': 'January 2017 Special Session',
            'start_date': "2017-04-04",
            'classification': 'special',
            'name': 'January 2017 Special Session',
            '_scraped_name': 'January 2017 Special Session',
        },
        {
            'identifier': 'August 2017 Special Session',
            'start_date': "2017-08-01",
            'classification': 'special',
            'name': 'August 2017 Special Session',
            '_scraped_name': 'August 2017 Special Session',
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2018-05-23",
            "identifier": "2017 Regular Session",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03"
        },
        {
            'identifier': 'January 2018 Special Session',
            'start_date': "2018-01-18",
            "end_date": "2018-02-27",
            'classification': 'special',
            'name': 'January 2018 Special Session',
            '_scraped_name': 'January 2018 Special Session',
        },
        {
            'identifier': 'March 2018 Special Session',
            'start_date': "2018-03-16",
            "end_date": "2018-03-29",
            'classification': 'special',
            'name': 'March 2018 Special Session',
            '_scraped_name': 'March 2018 Special Session',
        },
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "end_date": "2020-05-23",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-07"
        },
    ]
    ignored_scraped_sessions = [
        "February 2015 Extraordinary Session",
        "2007 Regular Session",
        "April 2008 Special Session",
        "March 2008 Special Session",
        "December 2007 Special Session",
        "October 2007 Special Session",
        "January 2007 Special Session",
        "February 2006 Special Session",
        "2005 Regular Session",
        "January 2005 Special Session",
        "2003 Regular Session",
        "January 2003 Special Session",
        "2001 Regular Session",
        "May 2002 Special Session",
        "January 2002 Special Session",
        "May 2001 Special Session",
        "1999 Regular Session",
        "May 2000 Special Session",
        "October 1999 Special Session",
        "1997 Regular Session",
        "April 1998 Special Session",
        "1995 Regular Session",
        "January 1995 Special Session",
        "September 1995 Special Session"
    ]

    def get_organizations(self):
        legislature_name = "Wisconsin State Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization('Senate', classification='upper', parent_id=legislature._id)
        lower = Organization('Assembly', classification='lower', parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath('http://docs.legis.wisconsin.gov/search',
                             "//select[@name='sessionNumber']/option/text()")
        return [session.strip(' -') for session in sessions]
