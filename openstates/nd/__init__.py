from pupa.scrape import Jurisdiction, Organization
from .committees import NDCommitteeScraper
from .votes import NDVoteScraper
from .people import NDPersonScraper
from .bills import NDBillScraper


class NorthDakota(Jurisdiction):
    division_id = "ocd-division/country:us/state:nd"
    classification = "government"
    name = "North Dakota"
    url = "http://www.legis.nd.gov/"
    scrapers = {
        'people': NDPersonScraper,
        'votes': NDVoteScraper,
        'committees': NDCommitteeScraper,
        'bills': NDBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "62nd Legislative Assembly (2011-12)",
            "identifier": "62",
            "name": "62nd Legislative Assembly (2011-2012)",
            "start_date": "2011-01-04"
        },
        {
            "_scraped_name": "63rd Legislative Assembly (2013-14)",
            "identifier": "63",
            "name": "63rd Legislative Assembly (2013-2014)",
            "start_date": "2013-01-08"
        },
        {
            "_scraped_name": "64th Legislative Assembly (2015-16)",
            "identifier": "64",
            "name": "64th Legislative Assembly (2015-2016)",
            "start_date": "2015-01-08"
        },
        {
            "_scraped_name": "65th Legislative Assembly (2017-18)",
            "identifier": "65",
            "name": "65th Legislative Assembly (2017-2018)",
            "start_date": "2017-01-03",
            "end_date": "2017-04-27",
        }
    ]
    ignored_scraped_sessions = [
        "61st Legislative Assembly (2009-10)",
        "60th Legislative Assembly (2007-08)",
        "59th Legislative Assembly (2005-06)",
        "58th Legislative Assembly (2003-04)",
        "57th Legislative Assembly (2001-02)",
        "56th Legislative Assembly (1999-2000)",
        "55th Legislative Assembly (1997-98)",
        "54th Legislative Assembly (1995-96)",
        "53rd Legislative Assembly (1993-94)",
        "52nd Legislative Assembly (1991-92)",
        "51st Legislative Assembly (1989-90)",
        "50th Legislative Assembly (1987-88)",
        "49th Legislative Assembly (1985-86)",
        "48th Legislative Assembly (1983-84)",
        "47th Legislative Assembly (1981-82)",
        "46th Legislative Assembly (1979-80)",
        "45th Legislative Assembly (1977-78)",
        "44th Legislative Assembly (1975-76)",
        "43rd Legislative Assembly (1973-74)",
        "42nd Legislative Assembly (1971-72)",
        "41st Legislative Assembly (1969-70)",
        "40th Legislative Assembly (1967-68)",
        "39th Legislative Assembly (1965-66)",
        "38th Legislative Assembly (1963-64)",
        "37th Legislative Assembly (1961-62)",
        "36th Legislative Assembly (1959-60)",
        "35th Legislative Assembly (1957-58)"
    ]

    def get_organizations(self):
        legislature_name = "North Dakota Legislative Assembly"
        lower_chamber_name = "House"
        lower_seats = 47
        lower_title = "Senator"
        upper_chamber_name = "Senate"
        upper_seats = 47
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
        import scrapelib
        import lxml.html

        url = 'http://www.legis.nd.gov/assembly/'
        html = scrapelib.Scraper().get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        return doc.xpath("//div[@class='view-content']//a/text()")
