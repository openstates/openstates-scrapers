from pupa.scrape import Jurisdiction, Organization

from .bills import ALBillScraper
from .events import ALEventScraper
# from .people import ALPersonScraper


class Alabama(Jurisdiction):
    division_id = "ocd-division/country:us/state:al"
    classification = "government"
    name = "Alabama"
    url = "http://www.legislature.state.al.us/"
    scrapers = {
        'bills': ALBillScraper,
        'events': ALEventScraper
        # 'people': ALPersonScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "Regular Session 2011",
            "classification": "primary",
            "identifier": "2011rs",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "First Special Session 2012",
            "classification": "special",
            "identifier": "2012fs",
            "name": "First Special Session 2012"
        },
        {
            "_scraped_name": "Regular Session 2012",
            "classification": "primary",
            "identifier": "2012rs",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "Regular Session 2013",
            "classification": "primary",
            "identifier": "2013rs",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "Regular Session 2014",
            "classification": "primary",
            "identifier": "2014rs",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "First Special Session 2015",
            "classification": "special",
            "identifier": "2015fs",
            "name": "First Special Session 2015"
        },
        {
            "_scraped_name": "Organizational Session 2015",
            "classification": "primary",
            "identifier": "2015os",
            "name": "2015 Organizational Session"
        },
        {
            "_scraped_name": "Regular Session 2015",
            "classification": "primary",
            "identifier": "2015rs",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "Second Special Session 2015",
            "classification": "special",
            "identifier": "2015ss",
            "name": "Second Special Session 2015"
        },
        {
            "_scraped_name": "First Special Session 2016",
            "classification": "special",
            "identifier": "2016fs",
            "name": "First Special Session 2016"
        },
        {
            "_scraped_name": "Regular Session 2016",
            "classification": "primary",
            "identifier": "2016rs",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "Regular Session 2017",
            "classification": "primary",
            "end_date": "2017-05-31",
            "identifier": "2017rs",
            "name": "2017 Regular Session",
            "start_date": "2017-02-07"
        },
        {
            "_scraped_name": "Regular Session 2018",
            "classification": "primary",
            "identifier": "2018rs",
            "name": "2018 Regular Session",
            "start_date": "2018-01-09"
        }
    ]
    ignored_scraped_sessions = [
        "Regular Session 1998",
        "Organizational Session 1999",
        "Regular Session 1999",
        "First Special Session 1999",
        "Organizational Session 2011",
        "Second Special Session 1999",
        "Regular Session 2000",
        "Regular Session 2001",
        "First Special Session 2001",
        "Second Special Session 2001",
        "Third Special Session 2001",
        "Fourth Special Session 2001",
        "Regular Session 2002",
        "Organizational Session 2003",
        "Regular Session 2003",
        "First Special Session 2003",
        "Second Special Session 2003",
        "Regular Session 2004",
        "First Special Session 2004",
        "Regular Session 2005",
        "First Special Session 2005",
        "Regular Session 2006",
        "Organizational Session 2007",
        "Regular Session 2007",
        "First Special Session 2007",
        "Regular Session 2008",
        "First Special Session 2008",
        "Regular Session 2009",
        "Regular Session 2010",
        "First Special Session 2009",
        "First Special Session 2010",
        "Regular Session 2016"
    ]

    def get_organizations(self):
        legislature_name = "Alabama Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        import lxml.html
        import requests

        s = requests.Session()
        r = s.get('http://alisondb.legislature.state.al.us/alison/SelectSession.aspx')
        doc = lxml.html.fromstring(r.text)
        return doc.xpath('//*[@id="ContentPlaceHolder1_gvSessions"]/tr/td/font/a/font/text()')
