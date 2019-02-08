import os

import requests
from pupa.scrape import Jurisdiction, Organization

from .people import INPersonScraper
# from .committees import INCommitteeScraper
from .bills import INBillScraper


class Indiana(Jurisdiction):
    division_id = "ocd-division/country:us/state:in"
    classification = "government"
    name = "Indiana"
    url = "http://www.in.gov/"
    scrapers = {
        'people': INPersonScraper,
        # 'committees': INCommitteeScraper,
        'bills': INBillScraper

    }
    legislative_sessions = [
        {
            "_scraped_name": "First Regular Session 116th General Assembly (2009)",
            "identifier": "2009",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "Second Regular Session 116th General Assembly (2010)",
            "identifier": "2010",
            "name": "2010 Regular Session"
        },
        {
            "_scraped_name": "First Regular Session 117th General Assembly (2011)",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-05"
        },
        {
            "_scraped_name": "Second Regular Session 117th General Assembly (2012)",
            "identifier": "2012",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "First Regular Session 118th General Assembly (2013)",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "Second Regular Session 118th General Assembly (2014)",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "First Regular Session 119th General Assembly (2015)",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "Second Regular Session 119th General Assembly (2016)",
            "identifier": "2016",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "First Regular Session 120th General Assembly (2017)",
            "end_date": "2017-04-29",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-09"
        },
        {
            "_scraped_name": "Second Regular Session 120th General Assembly (2018)",
            "identifier": "2018",
            "name": "2018 Regular Session"
        },
        {
            "_scraped_name": "Special Session 120th General Assembly (2018)",
            "identifier": "2018ss1",
            "name": "2018 Special Session",
            "start_date": "2018-05-14",
            "end_date": "2018-05-24",
        },
        {
            "_scraped_name": "First Regular Session 121st General Assembly (2019)",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-14"
        },
    ]
    ignored_scraped_sessions = [
        "First Regular Session 121st General Assembly (2019)",
        "2012 Regular Session",
        "2011 Regular Session",
        "2010 Regular Session",
        "2009 Special Session",
        "2009 Regular Session",
        "2008 Regular Session",
        "2007 Regular Session",
        "2006 Regular Session",
        "2005 Regular Session",
        "2004 Regular Session",
        "2003 Regular Session",
        "2002 Special Session",
        "2002 Regular Session",
        "2001 Regular Session",
        "2000 Regular Session",
        "1999 Regular Session",
        "1998 Regular Session",
        "1997 Regular Session"
    ]

    def get_organizations(self):
        legislature_name = "Indiana General Assembly"

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
        apikey = os.environ['INDIANA_API_KEY']
        useragent = os.environ['USER_AGENT'] or "openstates"
        headers = {"Authorization": apikey,
                   "Accept": "application/json",
                   "User-Agent": useragent}
        resp = requests.get("https://api.iga.in.gov/sessions", headers=headers)
        resp.raise_for_status()
        return [session["name"] for session in resp.json()["items"]]
