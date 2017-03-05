from pupa.scrape import Jurisdiction, Organization
from .people import NCPersonScraper
from .committees import NCCommitteeScraper
from .bills import NCBillScraper


class NorthCarolina(Jurisdiction):
    division_id = "ocd-division/country:us/state:nc"
    classification = "government"
    name = "North Carolina"
    url = "TODO"
    scrapers = {
        'people': NCPersonScraper,
        'committees': NCCommitteeScraper,
        'bills': NCBillScraper,
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
    legislative_sessions = [
        {
            "_scraped_name": "2009-2010 Session",
            "classification": "primary",
            "identifier": "2009",
            "name": "2009-2010 Session",
            "start_date": "2009-01-28"
        },
        {
            "_scraped_name": "2011-2012 Session",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011-2012 Session",
            "start_date": "2011-01-26"
        },
        {
            "_scraped_name": "2013-2014 Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013-2014 Session",
            "start_date": "2013-01-30"
        },
        {
            "_scraped_name": "2015-2016 Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015-2016 Session",
            "start_date": "2015-01-30"
        },
        {
            "_scraped_name": "2016 Extra Session 1",
            "classification": "special",
            "identifier": "2015E1",
            "name": "2016 Extra Session 1",
        },
        {
            "_scraped_name": "2016 Extra Session 2",
            "classification": "special",
            "identifier": "2015E2",
            "name": "2016 Extra Session 2",
        },
        {
            "_scraped_name": "2016 Extra Session 3",
            "classification": "special",
            "identifier": "2015E3",
            "name": "2016 Extra Session 3",
        },
        {
            "_scraped_name": "2016 Extra Session 4",
            "classification": "special",
            "identifier": "2015E4",
            "name": "2016 Extra Session 4",
        },
        {
            "_scraped_name": "2016 Extra Session 5",
            "classification": "special",
            "identifier": "2015E5",
            "name": "2016 Extra Session 5",
        },
        {
            "_scraped_name": "2017-2018 Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017-2018 Session",
        },
    ]
    ignored_scraped_sessions = [
        '2008 Extra Session',
        '2007-2008 Session',
        '2007 Extra Session',
        '2005-2006 Session',
        '2004 Extra Session',
        '2003-2004 Session',
        '2003 Extra Session 1',
        '2003 Extra Session 2',
        '2002 Extra Session',
        '2001-2002 Session',
        '2000 Special Session',
        '1999-2000 Session',
        '1999 Special Session',
        '1998 Special Session',
        '1997-1998 Session',
        '1996 2nd Special Session',
        '1996 1st Special Session',
        '1995-1996 Session',
        '1994 Special Session',
        '1993-1994 Session',
        '1991-1992 Session',
        '1991 Special Session',
        '1990 Special Session',
        '1989-1990 Session',
        '1989 Special Session',
        '1987-1988 Session',
        '1986 Special Session',
        '1985-1986 Session',
    ]

    def get_organizations(self):
        legislature_name = "North Carolina General Assembly"
        lower_chamber_name = "House"
        lower_seats = 120
        lower_title = "Representative"
        upper_chamber_name = "Senate"
        upper_seats = 50
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats+1):
            lower.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            upper.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
