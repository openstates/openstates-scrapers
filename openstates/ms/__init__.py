from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath

# from .people import MSLegislatorScraper
# from .committees import MSCommitteeScraper
from .bills import MSBillScraper


class Mississippi(Jurisdiction):
    division_id = "ocd-division/country:us/state:ms"
    classification = "government"
    name = "Mississippi"
    url = "http://www.legislature.ms.gov/"
    scrapers = {
        # "people": MSLegislatorScraper,
        # "committees": MSCommitteeScraper,
        "bills": MSBillScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2008 Regular Session",
            "identifier": "2008",
            "name": "2008 Regular Session"
        },
        {
            "_scraped_name": "2009 Regular Session",
            "identifier": "2009",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "2009 First Extraordinary Session",
            "identifier": "20091E",
            "name": "2009, 1st Extraordinary Session"
        },
        {
            "_scraped_name": "2009 Second Extraordinary Session",
            "identifier": "20092E",
            "name": "2009, 2nd Extraordinary Session"
        },
        {
            "_scraped_name": "2009 Third Extraordinary Session",
            "identifier": "20093E",
            "name": "2009, 3rd Extraordinary Session"
        },
        {
            "_scraped_name": "2010 Regular Session",
            "identifier": "2010",
            "name": "2010 Regular Session"
        },
        {
            "_scraped_name": "2010 First Extraordinary Session",
            "identifier": "20101E",
            "name": "2010, 1st Extraordinary Session"
        },
        {
            "_scraped_name": "2010 Second Extraordinary Session",
            "identifier": "20102E",
            "name": "2010, 2nd Extraordinary Session"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "identifier": "2011",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "2011 First Extraordinary Session",
            "identifier": "20111E",
            "name": "2011, 1st Extraordinary Session"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "identifier": "2012",
            "name": "2012 Regular Session"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2013 First Extraordinary Session",
            "identifier": "20131E",
            "name": "2013 First Extraordinary Session"
        },
        {
            "_scraped_name": "2013 Second Extraordinary Session",
            "identifier": "20132E",
            "name": "2013 Second Extraordinary Session"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2014 First Extraordinary Session",
            "identifier": "20141E",
            "name": "2014 First Extraordinary Session"
        },
        {
            "_scraped_name": "2014 Second Extraordinary Session",
            "identifier": "20142E",
            "name": "2014 Second Extraordinary Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "end_date": "2016-05-08",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-05"
        },
        {
            "_scraped_name": "2016 First Extraordinary Session",
            "identifier": "20161E",
            "name": "2016 First Extraordinary Session"
        },
        {
            "_scraped_name": "2016 Second Extraordinary Session",
            "identifier": "20162E",
            "name": "2016 Second Extraordinary Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-03"
        },
        {
            "_scraped_name": "2017 First Extraordinary Session",
            "classification": "special",
            "identifier": "20171E",
            "name": "2017 First Extraordinary Session",
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "end_date": "2018-04-01",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-02"
        },
        {
            "_scraped_name": "2018 First Extraordinary Session",
            "classification": "special",
            "identifier": "20181E",
            "name": "2018 First Extraordinary Session",
            "start_date": "2018-08-23",
        },
    ]
    ignored_scraped_sessions = [
        "2008 First Extraordinary Session",
        "2007 Regular Session",
        "2007 First Extraordinary Session",
        "2006 Regular Session",
        "2006 First Extraordinary Session",
        "2006 Second Extraordinary Session",
        "2005 Regular Session",
        "2005 First Extraordinary Session",
        "2005 Second Extraordinary Session",
        "2005 Third Extraordinary Session",
        "2005 Fourth Extraordinary Session",
        "2005 Fifth Extraordinary Session",
        "2004 Regular Session",
        "2004 First Extraordinary Session",
        "2004 Second Extraordinary Session",
        "2004 Third Extraordinary Session",
        "2003 Regular Session",
        "2002 Regular Session",
        "2002 First Extraordinary Session",
        "2002 Second Extraordinary Session",
        "2002 Third Extraordinary Session",
        "2001 Regular Session",
        "2001 First Extraordinary Session",
        "2001 Second Extraordinary Session",
        "2000 Regular Session",
        "2000 First Extraordinary Session",
        "2000 Second Extraordinary Session",
        "2000 Third Extraordinary Session",
        "1999 Regular Session",
        "1998 Regular Session",
        "1997 Regular Session"
    ]

    def get_organizations(self):
        legislature_name = "Mississippi Legislature"
        upper_chamber_name = "Senate"
        lower_chamber_name = "House"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name='Office of the Governor',
                                 classification='executive')
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('http://billstatus.ls.state.ms.us/sessions.htm',
                         '//a/text()')
