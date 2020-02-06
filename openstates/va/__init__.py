import logging
from openstates.utils import url_xpath, State

from .people import VaPersonScraper
from .bills import VaBillScraper


logging.getLogger(__name__).addHandler(logging.NullHandler())


settings = {"SCRAPELIB_RPM": 40}


class Virginia(State):
    scrapers = {"people": VaPersonScraper, "bills": VaBillScraper}
    legislative_sessions = [
        {
            "_scraped_name": "2010 Session",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-13",
        },
        {
            "_scraped_name": "2011 Session",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-12",
        },
        {
            "_scraped_name": "2011 Special Session I",
            "identifier": "2011specialI",
            "name": "2011, 1st Special Session",
        },
        {
            "_scraped_name": "2012 Session",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11",
        },
        {
            "_scraped_name": "2012 Special Session I",
            "identifier": "2012specialI",
            "name": "2012, 1st Special Session",
            "start_date": "2012-03-11",
        },
        {
            "_scraped_name": "2013 Session",
            "identifier": "2013",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
        },
        {
            "_scraped_name": "2013 Special Session I",
            "identifier": "2013specialI",
            "name": "2013, 1st Special Session",
        },
        {
            "_scraped_name": "2014 Session",
            "identifier": "2014",
            "name": "2014 Regular Session",
            "start_date": "2014-01-09",
        },
        {
            "_scraped_name": "2014 Special Session I",
            "identifier": "2014specialI",
            "name": "2014, 1st Special Session",
        },
        {
            "_scraped_name": "2015 Session",
            "end_date": "2015-02-27",
            "identifier": "2015",
            "name": "2015 Regular Session",
            "start_date": "2015-01-14",
        },
        {
            "_scraped_name": "2015 Special Session I",
            "end_date": "2015-08-17",
            "identifier": "2015specialI",
            "name": "2015, 1st Special Session",
            "start_date": "2015-08-17",
        },
        {
            "_scraped_name": "2016 Session",
            "end_date": "2016-03-12",
            "identifier": "2016",
            "name": "2016 Regular Session",
            "start_date": "2016-01-13",
        },
        {
            "_scraped_name": "2017 Session",
            "end_date": "2017-02-09",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
        },
        {
            "_scraped_name": "2018 Session",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-10",
        },
        {
            "_scraped_name": "2018 Special Session I",
            "identifier": "2018specialI",
            "name": "2018, 1st Special Session",
            "start_date": "2018-04-11",
        },
        {
            "_scraped_name": "2018 Special Session II",
            "identifier": "2018specialI",
            "name": "2018, 2nd Special Session",
            "start_date": "2018-08-30",
        },
        {
            "_scraped_name": "2019 Session",
            "identifier": "2019",
            "name": "2019 Regular Session",
            "start_date": "2019-01-09",
        },
        {
            "_scraped_name": "2019 Special Session I",
            "identifier": "2019specialI",
            "name": "2019, 1st Special Session",
            "start_date": "2019-07-09",
        },
        {
            "_scraped_name": "2020 Session",
            "identifier": "2020",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
        },
    ]
    ignored_scraped_sessions = [
        "2015 Special Session I",
        "2015 Session",
        "2014 Special Session I",
        "2014 Session",
        "2013 Special Session I",
        "2013 Session",
        "2012 Special Session I",
        "2012 Session",
        "2011 Special Session I",
        "2011 Session",
        "2010 Session",
        "2009 Session",
        "2009 Special Session I",
        "2008 Session",
        "2008 Special Session I",
        "2008 Special Session II",
        "2007 Session",
        "2006 Session",
        "2006 Special Session I",
        "2005 Session",
        "2004 Session",
        "2004 Special Session I",
        "2004 Special Session II",
        "2003 Session",
        "2002 Session",
        "2001 Session",
        "2001 Special Session I",
        "2000 Session",
        "1999 Session",
        "1998 Session",
        "1998 Special Session I",
        "1997 Session",
        "1996 Session",
        "1995 Session",
        "1994 Session",
        "1994 Special Session I",
        "1994 Special Session II",
    ]

    def get_session_list(self):
        sessions = url_xpath(
            "http://lis.virginia.gov/", "//div[@id='sLink']//select/option/text()"
        )
        return [s.strip() for s in sessions if "Session" in s]
