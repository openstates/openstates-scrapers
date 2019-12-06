from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from openstates.mo.bills import MOBillScraper
from openstates.mo.events import MOEventScraper
# from openstates.mo.votes import MOVoteScraper
from openstates.mo.people import MOPersonScraper
# from openstates.mo.committees import MOCommitteeScraper


class Missouri(Jurisdiction):
    division_id = "ocd-division/country:us/state:mo"
    classification = "government"
    name = "Missouri"
    url = "http://www.moga.mo.gov/"
    scrapers = {
        'bills': MOBillScraper,
        # 'votes': MOVoteScraper,
        'events': MOEventScraper,
        'people': MOPersonScraper,
        # 'committees': MOCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
            "end_date": "2019-05-17",
        },
        {
            "_scraped_name": "2019 1st Extraordinary Session",
            "classification": "primary",
            "identifier": "2019S1",
            "name": "2019 First Extraordinary Session",
            "start_date": "2019-09-09",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "classification": "primary",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
        },
    ]
    ignored_scraped_sessions = [
        '2018 Regular Session',
        '2018 Special Session',
        '2018 1st Extraordinary Session',
        '2007 Regular Session',
        '2010 Extraordinary Session',
        '2002 Regular Session',
        '1999 Regular Session',
        '2013 Extraordinary Session',
        '2007 Extraordinary Session',
        '2003 2nd Extraordinary Session',
        '2014 Regular Session',
        '2017 Extraordinary Session',
        '2005 Regular Session',
        '2011 Extraordinary Session',
        '2006 Regular Session',
        '2004 Regular Session',
        '2015 Regular Session',
        '2003 1st Extraordinary Session',
        '2010 Regular Session',
        '2001 Regular Session',
        '2017 2nd Extraordinary Session',
        '2003 Regular Session',
        '2009 Regular Session',
        '2005 Extraordinary Session',
        '2017 Regular Session',
        '2000 Regular Session',
        '2013 Regular Session',
        '2011 Regular Session',
        '2001 Extraordinary Session',
        '2012 Regular Session',
        '2008 Regular Session',
        '2016 Regular Session',
        '2019 1st Extraordinary Session',
    ]

    def get_organizations(self):
        legislature_name = "Missouri General Assembly"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield Organization(name='Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'https://www.house.mo.gov/billcentral.aspx?year=2019&code=S1&q=&id=',
            '//select[@id="SearchSession"]/option/text()')
