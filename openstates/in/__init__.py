from pupa.scrape import Jurisdiction, Organization


class Indiana(Jurisdiction):
    division_id = "ocd-division/country:us/state:in"
    classification = "government"
    name = "Indiana"
    url = "http://www.in.gov/"
    scrapers = {
    }
    parties = [
        {'name': 'Republican'},
        {'name': 'Democratic'}
    ]
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
        }
    ]
    ignored_scraped_sessions = [
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
        lower_chamber_name = "House"
        lower_seats = 100
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
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats+1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower
