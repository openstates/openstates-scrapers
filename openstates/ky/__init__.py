import re

from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .people import KYPersonScraper
from .committees import KYCommitteeScraper
from .bills import KYBillScraper


class Kentucky(Jurisdiction):
    division_id = "ocd-division/country:us/state:ky"
    classification = "government"
    name = "Kentucky"
    url = "http://www.lrc.ky.gov/"
    scrapers = {
        'people': KYPersonScraper,
        'committees': KYCommitteeScraper,
        'bills': KYBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2011-03-09",
            "identifier": "2011 Regular Session",
            "name": "2011 Regular Session",
            "start_date": "2011-01-04"
        },
        {
            "_scraped_name": "2011 Extraordinary Session",
            "classification": "special",
            "end_date": "2011-04-06",
            "identifier": "2011SS",
            "name": "2011 Extraordinary Session",
            "start_date": "2011-03-14"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "end_date": "2012-04-12",
            "identifier": "2012RS",
            "name": "2012 Regular Session",
            "start_date": "2012-01-03"
        },
        {
            "_scraped_name": "2012 Extraordinary Session",
            "classification": "special",
            "end_date": "2012-04-20",
            "identifier": "2012SS",
            "name": "2012 Extraordinary Session",
            "start_date": "2012-04-16"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "end_date": "2013-03-26",
            "identifier": "2013RS",
            "name": "2013 Regular Session",
            "start_date": "2013-01-08"
        },
        {
            "_scraped_name": "2013 Extraordinary Session",
            "classification": "special",
            "end_date": "2013-08-19",
            "identifier": "2013SS",
            "name": "2013 Extraordinary Session",
            "start_date": "2013-08-19"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "classification": "primary",
            "end_date": "2014-04-15",
            "identifier": "2014RS",
            "name": "2014 Regular Session",
            "start_date": "2014-01-07"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "end_date": "2015-03-25",
            "identifier": "2015RS",
            "name": "2015 Regular Session",
            "start_date": "2015-01-06"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "end_date": "2016-04-12",
            "identifier": "2016RS",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2017-03-30",
            "identifier": "2017RS",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03"
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "end_date": "2018-04-13",
            "identifier": "2018RS",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02"
        },
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "Kentucky General Assembly"
        lower_chamber_name = "House"
        lower_seats = 100
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 38
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

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        sessions = url_xpath(
            'http://www.lrc.ky.gov/legislation.htm',
            '//a[contains(@href, "record.htm")]/text()[normalize-space()]')

        for index, session in enumerate(sessions):
            # Remove escaped whitespace characters.
            sessions[index] = re.sub(r'[\r\n\t]+', '', session)

        return sessions
