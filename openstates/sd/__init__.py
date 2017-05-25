from pupa.scrape import Jurisdiction, Organization
import scrapelib
import lxml.html
from .people import SDLegislatorScraper
from .bills import SDBillScraper


class SouthDakota(Jurisdiction):
    division_id = "ocd-division/country:us/state:sd"
    classification = "government"
    name = "South Dakota"
    url = "http://www.sdlegislature.gov/"
    scrapers = {
        'people': SDLegislatorScraper,
        'bills': SDBillScraper
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009 (84th) Session",
            "identifier": "2009",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "2010 (85th) Session",
            "identifier": "2010",
            "name": "2010 Regular Session"
        },
        {
            "_scraped_name": "2011 (86th) Session",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-11"
        },
        {
            "_scraped_name": "2011 (86th) Special Session",
            "identifier": "2011s",
            "name": "2011 Special Session"
        },
        {
            "_scraped_name": "2012 (87th) Session",
            "identifier": "2012",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "2013 (88th) Session",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014 (89th) Session",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 (90th) Session",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 (91st) Session",
            "identifier": "2016",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017 (92nd) Session",
            "identifier": "2017",
            "name": "2017 Regular Session"
        },
        {
            "_scraped_name": "2017 (92nd) Special Session",
            "identifier": "2017s",
            "name": "2017 Special Session"
        }
    ]
    ignored_scraped_sessions = [
        "Previous Years"
    ]

    def get_organizations(self):
        legislature_name = "South Dakota State Legislature"
        lower_chamber_name = "House"
        lower_seats = 0
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 0
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
        html = scrapelib.Scraper().get('http://www.sdlegislature.gov/'
                                       'Legislative_Session/Menu.aspx').text
        doc = lxml.html.fromstring(html)
        sessions = doc.xpath('//div[@id="ctl00_ContentPlaceHolder1_BlueBoxLeft"]//ul/li'
                             '/a/div/text()')
        return sessions
