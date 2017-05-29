import os
import csv
from pupa.scrape import Jurisdiction, Organization
from .people import NHPersonScraper
from .committees import NHCommitteeScraper
from .bills import NHBillScraper


class NewHampshire(Jurisdiction):
    division_id = "ocd-division/country:us/state:nh"
    classification = "government"
    name = "New Hampshire"
    url = "TODO"
    scrapers = {
        'people': NHPersonScraper,
        'committees': NHCommitteeScraper,
        'bills': NHBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2011 Session",
            "identifier": "2011",
            "name": "2011 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2011%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2012 Session",
            "identifier": "2012",
            "name": "2012 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2012%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2013",
            "identifier": "2013",
            "name": "2013 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2013%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2014 Session",
            "identifier": "2014",
            "name": "2014 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2014%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2015 Session",
            "identifier": "2015",
            "name": "2015 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2015%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2016 Session",
            "identifier": "2016",
            "name": "2016 Regular Session",
            'zip_url': ('http://gencourt.state.nh.us/downloads/2016%'
                        '20Session%20Bill%20Status%20Tables.zip'),
        },
        {
            "_scraped_name": "2017 Session",
            "identifier": "2017",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = [
        "2013 Session",
        "2017 Session Bill Status Tables Link.txt"
    ]

    def get_organizations(self):
        legislature_name = "New Hampshire General Court"
        lower_chamber_name = "House"
        # lower_seats = None
        lower_title = "Senator"
        upper_chamber_name = "Senate"
        # upper_seats = 0
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        # NH names all their districts, so pull them manually.
        csv_file = '{}/../../manual_data/districts/nh.csv'.format(os.path.dirname(__file__))
        with open(csv_file, mode='r') as infile:
            districts = csv.DictReader(infile)
            for district in districts:
                if district['chamber'] == 'lower':
                    lower.add_post(
                        label=district['name'],
                        role=lower_title,
                        division_id=district['division_id'])
                elif district['chamber'] == 'upper':
                    lower.add_post(
                        label=district['name'],
                        role=upper_title,
                        division_id=district['division_id'])

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        from openstates.utils import url_xpath
        zips = url_xpath('http://gencourt.state.nh.us/downloads/',
                         '//a[contains(@href, "Bill%20Status%20Tables")]/text()')
        return [zip.replace(' Bill Status Tables.zip', '') for zip in zips]
