from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from openstates.mo.bills import MOBillScraper
from openstates.mo.votes import MOVoteScraper
from openstates.mo.people import MOPersonScraper
from openstates.mo.committees import MOCommitteeScraper


class Missouri(Jurisdiction):
    division_id = "ocd-division/country:us/state:mo"
    classification = "government"
    name = "Missouri"
    url = "http://www.moga.mo.gov/"
    scrapers = {
        'bills': MOBillScraper,
        'votes': MOVoteScraper,
        'people': MOPersonScraper,
        'committees': MOCommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2012 - 96th General Assembly - 2nd Regular Session",
            "classification": "primary",
            "end_date": "2012-05-30",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-04"
        },
        {
            "_scraped_name": "2013 - 97th General Assembly - 1st Regular Session",
            "classification": "primary",
            "end_date": "2013-05-30",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09"
        },
        {
            "_scraped_name": "2014 - 97th General Assembly - 2nd Regular Session",
            "classification": "primary",
            "end_date": "2014-05-30",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-08"
        },
        {
            "_scraped_name": "2015 - 98th General Assembly - 1st Regular Session",
            "classification": "primary",
            "end_date": "2015-05-30",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07"
        },
        {
            "classification": "primary",
            "end_date": "2016-05-30",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-06"
        },
        {
            "classification": "primary",
            "end_date": "2017-05-12",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-04"
        },
        {
            "classification": "special",
            "identifier": "2017S1",
            "name": "2017 First Extraordinary Session",
            "start_date": "2017-06-01",
        },
        {
            "classification": "special",
            "identifier": "2017S2",
            "name": "2017 Second Extraordinary Session",
            "start_date": "2017-07-25",
        },
        
    ]
    ignored_scraped_sessions = [
        "2014 - 97th General Assembly - 2nd Regular Session",
        "2013 - 97th General Assembly - 1st Regular Session",
        "2012 - 96th General Assembly - 2nd Regular Session",
        "2011 - 96th General Assembly - 1st Regular Session",
        "2010 - 95th General Assembly - 2nd Regular Session",
        "2009 - 95th General Assembly - 1st Regular Session",
        "2008 - 94th General Assembly - 2nd Regular Session",
        "2007 - 94th General Assembly - 1st Regular Session",
        "2006 - 93rd General Assembly - 2nd Regular Session",
        "2005 - 93rd General Assembly - 1st Regular Session",
        "2004 - 92nd General Assembly - 2nd Regular Session",
        "2003 - 92nd General Assembly - 1st Regular Session",
        "2002 - 91st General Assembly - 2nd Regular Session",
        "2001 - 91st General Assembly - 1st Regular Session",
        "2000 - 90th General Assembly - 2nd Regular Session",
        "1999 - 90th General Assembly - 1st Regular Session",
        "1998 - 89th General Assembly - 2nd Regular Session",
        "1997 - 89th General Assembly - 1st Regular Session",
        "1996 - 88th General Assembly - 2nd Regular Session",
        "1995 - 88th General Assembly - 1st Regular Session"
    ]

    def get_organizations(self):
        legislature_name = "Missouri General Assembly"
        lower_chamber_name = "House"
        lower_seats = 163
        lower_title = "Senator"
        upper_chamber_name = "Senate"
        upper_seats = 34
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'http://www.senate.mo.gov/pastsessions.htm',
            '//div[@id="list"]/li/a/text()',
        )
