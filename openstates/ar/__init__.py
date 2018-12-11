from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

# from .people import ARLegislatorScraper
from .bills import ARBillScraper
# from .committees import ARCommitteeScraper
# from .events import AREventScraper


class Arkansas(Jurisdiction):
    division_id = "ocd-division/country:us/state:ar"
    classification = "government"
    name = "Arkansas"
    url = "http://www.arkleg.state.ar.us"
    scrapers = {
        # 'people': ARLegislatorScraper,
        # 'committees': ARCommitteeScraper,
        'bills': ARBillScraper,
        # 'events': AREventScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "Regular Session, 2011",
            "classification": "primary",
            "end_date": "2011-04-27",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-10"
        },
        {
            "_scraped_name": "Fiscal Session 2012",
            "classification": "special",
            "end_date": "2012-03-09",
            "identifier": "2012F",
            "name": "2012 Fiscal Session",
            "start_date": "2012-02-13"
        },
        {
            "_scraped_name": "Regular Session, 2013",
            "classification": "primary",
            "end_date": "2013-05-17",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-14"
        },
        {
            "_scraped_name": "First Extraordinary Session, 2013",
            "classification": "special",
            "end_date": "2013-10-19",
            "identifier": "2013S1",
            "name": "2013 First Extraordinary Session",
            "start_date": "2013-10-17"
        },
        {
            "_scraped_name": "Regular Session, 2014",
            "classification": "primary",
            "end_date": "2014-03-19",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-02-10"
        },
        {
            "_scraped_name": "Fiscal Session, 2014",
            "classification": "special",
            "end_date": "2014-03-19",
            "identifier": "2014F",
            "name": "2014 Fiscal Session",
            "start_date": "2014-02-10"
        },
        {
            "_scraped_name": "Second Extraordinary Session, 2014",
            "classification": "special",
            "end_date": "2014-07-02",
            "identifier": "2014S2",
            "name": "2014 Second Extraordinary Session",
            "start_date": "2014-06-30"
        },
        {
            "_scraped_name": "Regular Session, 2015",
            "classification": "primary",
            "end_date": "2015-04-22",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-12"
        },
        {
            "_scraped_name": "First Extraordinary Session, 2015",
            "classification": "special",
            "end_date": "2015-05-28",
            "identifier": "2015S1",
            "name": "2015 First Extraordinary Session",
            "start_date": "2015-05-26"
        },
        {
            "_scraped_name": "Fiscal Session, 2016",
            "classification": "special",
            "end_date": "2016-05-09",
            "identifier": "2016F",
            "name": "2016 Fiscal Session",
            "start_date": "2016-04-13"
        },
        {
            "_scraped_name": "Second Extraordinary Session, 2016",
            "classification": "special",
            "end_date": "2016-04-06",
            "identifier": "2016S2",
            "name": "2016 Second Extraordinary Session",
            "start_date": "2016-04-06"
        },
        {
            "_scraped_name": "Third Extraordinary Session, 2016",
            "classification": "special",
            "identifier": "2016S3",
            "name": "2016 Third Extraordinary Session",
            "start_date": "2016-05-19"
        },
        {
            "_scraped_name": "Regular Session, 2017",
            "classification": "primary",
            "end_date": "2017-04-22",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-12"
        },
        {
            "_scraped_name": "First Extraordinary Session, 2017",
            "classification": "special",
            "end_date": "2017-07-01",
            "identifier": "2017S1",
            "name": "2017 First Extraordinary Session",
            "start_date": "2017-05-01"
        },
        {
            "_scraped_name": "Fiscal Session, 2018",
            "classification": "special",
            "end_date": "2018-03-12",
            "identifier": "2018F",
            "name": "2018 Fiscal Session",
            "start_date": "2018-02-12"
        },
        {
            "_scraped_name": "Second Extraordinary Session, 2018",
            "classification": "special",
            "identifier": "2018S2",
            "name": "2018 Second Extraordinary Session",
            "start_date": "2018-03-13"
        },
        {
            "_scraped_name": "Regular Session, 2019",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-14"
        },
    ]
    ignored_scraped_sessions = [
        "Regular Session, 2009",
        "Fiscal Session, 2010",
        "Regular Session, 2007",
        "First Extraordinary Session, 2008",
        "Regular Session, 2005",
        "First Extraordinary Session, 2006 ",
        "Regular Session, 2003 ",
        "First Extraordinary Session, 2003",
        "Second Extraordinary Session, 2003",
        "Regular Session, 2001 ",
        "First Extraordinary Session, 2002",
        "Regular Session, 1999",
        "First Extraordinary Session, 2000",
        "Second Extraordinary Session, 2000",
        "Regular Session, 1997 ",
        "Regular Session, 1995 ",
        "First Extraordinary Session, 1995 ",
        "Regular Session, 1993 ",
        "First Extraordinary Session, 1993 ",
        "Second Extraordinary Session, 1993",
        "Regular Session, 1991",
        "First Extraordinary Session, 1991 ",
        "Second Extraordinary Session, 1991 ",
        "Regular Session, 1989",
        "First Extraordinary Session, 1989",
        "Second Extraordinary Session, 1989",
        "Third Extraordinary Session, 1989 ",
        "Regular Session, 1987 ",
        "First Extraordinary Session, 1987",
        "Second Extraordinary Session, 1987",
        "Third Extraordinary Session, 1987",
        "Fourth Extraordinary Session, 1987"
    ]

    def get_organizations(self):
        legislature_name = "Arkansas General Assembly"
        lower_chamber_name = "House"
        upper_chamber_name = "Senate"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        links = url_xpath('http://www.arkleg.state.ar.us/assembly/2013/2013R/Pages'
                          '/Previous%20Legislatures.aspx', '//a')
        sessions = [a.text_content() for a in links if 'Session' in a.attrib.get(
                    'title', '')]
        return sessions
