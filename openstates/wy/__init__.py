from pupa.scrape import Jurisdiction, Organization

from .bills import WYBillScraper
from .people import WYPersonScraper
# from .committees import WYCommitteeScraper

import requests
import re


class Wyoming(Jurisdiction):
    division_id = "ocd-division/country:us/state:wy"
    classification = "government"
    name = "Wyoming"
    url = "http://legisweb.state.wy.us/"
    scrapers = {
        'bills': WYBillScraper,
        'people': WYPersonScraper,
        # 'committees': WYCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011"
        },
        {
            "_scraped_name": "2012",
            "classification": "special",
            "identifier": "2012",
            "name": "2012"
        },
        {
            "_scraped_name": "2013",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013"
        },
        {
            "_scraped_name": "2014",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014"
        },
        {
            "_scraped_name": "2015",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015"
        },
        {
            "_scraped_name": "2016",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016"
        },
        {
            "_scraped_name": "2017",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017",
            "start_date": "2017-01-10",
            "end_date": "2017-03-03",
        },
        {
            "_scraped_name": "2018",
            "classification": "primary",
            "identifier": "2018",
            "name": "2018",
            "start_date": "2018-02-12",
            "end_date": "2018-03-16",
        },
        {
            "_scraped_name": "2019",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019 General Session",
            "start_date": "2019-02-12",
            "end_date": "2019-03-05",
        },
    ]
    ignored_scraped_sessions = [
        "2019",
        "2016",
        "2014",
        "2010",
        "2009",
        "2008",
        "2007",
        "2006",
        "2005",
        "2004",
        "2003",
        "2002",
        "2001"
    ]

    def get_organizations(self):
        legislature_name = "Wyoming State Legislature"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield Organization(name='Governor of Wyoming', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        # the sessions list is a JS object buried in a massive file
        # it looks like:
        # .constant("YEAR_VALUES",[{year:2001,title:"General Session",isActive:!0}, ...
        session = requests.Session()
        js = session.get('http://wyoleg.gov/js/site.min.js').content.decode('utf-8')
        # seriously, there must be a better way to do this
        sessions_regex = r'constant\(\"YEAR_VALUES\",\[(.*)\)}\(\),function\(w'
        sessions_string = re.search(sessions_regex, js)
        # once we have the big string, pull out year:2001, etc
        year_regex = r'year\:(\d+)'
        years = re.findall(year_regex, sessions_string.groups(0)[0])
        return years
