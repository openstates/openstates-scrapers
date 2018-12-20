from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath
from openstates.ne.bills import NEBillScraper
# from openstates.ne.votes import NEVoteScraper
from openstates.ne.people import NEPersonScraper
# from openstates.ne.committees import NECommitteeScraper


class Nebraska(Jurisdiction):
    division_id = "ocd-division/country:us/state:ne"
    classification = "government"
    name = "Nebraska"
    url = "http://nebraskalegislature.gov/"
    scrapers = {
        'bills': NEBillScraper,
        # 'votes': NEVoteScraper,
        'people': NEPersonScraper,
        # 'committees': NECommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "102nd Legislature 1st and 2nd Sessions",
            "end_date": "2012-04-18",
            "identifier": "102",
            "name": "102nd Legislature (2011-2012)",
            "start_date": "2011-01-05"
        },
        {
            "_scraped_name": "102nd Legislature 1st Special Session",
            "end_date": "2011-11-22",
            "identifier": "102S1",
            "name": "102nd Legislature, 1st Special Session (2011)",
            "start_date": "2011-11-01"
        },
        {
            "_scraped_name": "103rd Legislature 1st and 2nd Sessions",
            "end_date": "2014-05-30",
            "identifier": "103",
            "name": "103rd Legislature (2013-2014)",
            "start_date": "2013-01-08"
        },
        {
            "_scraped_name": "104th Legislature 1st and 2nd Sessions",
            "end_date": "2016-12-31",
            "identifier": "104",
            "name": "104th Legislature (2015-2016)",
            "start_date": "2015-01-07"
        },
        {
            "_scraped_name": "105th Legislature 1st and 2nd Sessions",
            "end_date": "2018-12-31",
            "identifier": "105",
            "name": "105th Legislature (2017-2018)",
            "start_date": "2017-01-04"
        }
    ]
    ignored_scraped_sessions = [
        "101st Legislature 1st and 2nd Sessions",
        "101st Legislature 1st Special Session",
        "100th Legislature 1st and 2nd Sessions",
        "100th Leg. First Special Session"
    ]

    def get_organizations(self):
        legislature_name = "Nebraska Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        executive = Organization(name='Office of the Governor',
                                 classification="executive")
        yield legislature
        yield executive

    def get_session_list(self):
        return url_xpath('http://nebraskalegislature.gov/bills/',
                         "//select[@name='Legislature']/option/text()")[:-1]
