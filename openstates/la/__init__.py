from pupa.scrape import Jurisdiction, Organization
from .people import LAPersonScraper
from .committees import LACommitteeScraper


class Louisiana(Jurisdiction):
    division_id = "ocd-division/country:us/state:la"
    classification = "government"
    name = "Louisiana"
    url = "http://www.legis.la.gov/"
    scrapers = {
        "people": LAPersonScraper,
        "committees": LACommitteeScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009 Regular Session",
            "classification": "primary",
            "end_date": "2010-06-24",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2010-04-27"
        },
        {
            "_scraped_name": "2010 Regular Session",
            "classification": "primary",
            "end_date": "2010-06-21",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-03-29"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2011-06-23",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-04-25"
        },
        {
            "_scraped_name": "2011 First Extraordinary Session",
            "classification": "special",
            "end_date": "2011-04-13",
            "identifier": "2011 1st Extraordinary Session",
            "name": "2011, 1st Extraordinary Session",
            "start_date": "2011-03-20"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "end_date": "2012-06-04",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-03-12"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "end_date": "2013-06-06",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-04-08"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "classification": "primary",
            "end_date": "2014-06-02",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-03-10"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "end_date": "2015-06-11",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-04-13"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "end_date": "2016-06-06",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-03-14"
        },
        {
            "_scraped_name": "2016 First Extraordinary Session",
            "classification": "special",
            "end_date": "2016-03-09",
            "identifier": "2016 1st Extraordinary Session",
            "name": "2016, 1st Extraordinary Session",
            "start_date": "2016-02-14"
        },
        {
            "_scraped_name": "2016 Second Extraordinary Session",
            "classification": "special",
            "end_date": "2016-06-23",
            "identifier": "2016 2nd Extraordinary Session",
            "name": "2016, 2nd Extraordinary Session",
            "start_date": "2016-06-06"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2017-06-08",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-04-10"
        },
        {
            "_scraped_name": "2017 First Extraordinary Session",
            "classification": "special",
            "end_date": "2017-02-22",
            "identifier": "2017 1st Extraordinary Session",
            "name": "2017, 1st Extraordinary Session",
            "start_date": "2017-02-13"
        }
    ]
    ignored_scraped_sessions = [
        "2016 Organizational Session",
        "2015 Regular Session",
        "2014 Regular Session",
        "2013 Regular Session",
        "2012 Regular Session",
        "2012 Organizational Session",
        "2011 Regular Session",
        "2011 First Extraordinary Session",
        "2010 Regular Session",
        "2009 Regular Session",
        "2008 Regular Session",
        "2008 Organizational Session",
        "2008 Second Extraordinary Session",
        "2008 First Extraordinary Session",
        "2007 Regular Session",
        "2006 Regular Session",
        "2005 Regular Session",
        "2004 Regular Session",
        "2004 First Extraordinary Session",
        "2004 1st Extraordinary Session",
        "2003 Regular Session",
        "2002 Regular Session",
        "2001 Regular Session",
        "2000 Regular Session",
        "1999 Regular Session",
        "1998 Regular Session",
        "1997 Regular Session",
        "2006 Second Extraordinary Session",
        "2006 First Extraordinary Session",
        "2005 First Extraordinary Session",
        "2002 First Extraordinary Session",
        "2001 Second Extraordinary Session",
        "2001 First Extraordinary Session",
        "2000 Second Extraordinary Session",
        "2000 First Extraordinary Session",
        "1998 First Extraordinary Session",
        "2012 Organizational Session",
        "2000 Organizational Session",
        "2004 Organizational Session",
        "Other Sessions",
        "Other Sessions",
        "Sessions"
    ]

    def get_organizations(self):
        legislature_name = "Louisiana Legislature"
        lower_chamber_name = "House"
        lower_seats = 105
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 39
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
