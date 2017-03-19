import csv
import os

from pupa.scrape import Jurisdiction, Organization
from .people import NHPersonScraper
from .bills import NHBillScraper

class NewHampshire(Jurisdiction):
    division_id = "ocd-division/country:us/state:nh"
    classification = "government"
    name = "New Hampshire"
    url = "http://gencourt.state.nh.us/"
    scrapers = {
        'people': NHPersonScraper,
        'bills': NHBillScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2017 Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session"
        }
    ]
    ignored_scraped_sessions = []

    def get_organizations(self):
        legislature_name = "New Hampshire General Court"
        lower_chamber_name = "House"
        lower_title = "Representative"
        upper_chamber_name = "Senate"
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
