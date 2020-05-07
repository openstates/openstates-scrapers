import re
from utils import url_xpath, State
from .people import COLegislatorScraper
from .bills import COBillScraper
from .events import COEventScraper

# from .committees import COCommitteeScraper


class Colorado(State):
    scrapers = {
        "people": COLegislatorScraper,
        # 'committees': COCommitteeScraper,
        "bills": COBillScraper,
        "events": COEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "identifier": "2011A",
            "name": "2011 Regular Session",
            "start_date": "2011-01-26",
            "end_date": "2011-05-11",
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "identifier": "2012A",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11",
            "end_date": "2012-05-09",
        },
        {
            "_scraped_name": "2012 First Extraordinary Session",
            "classification": "special",
            "identifier": "2012B",
            "name": "2012 First Extraordinary Session",
            "start_date": "2012-05-14",
            "end_date": "2012-05-16",
        },
        {
            "_scraped_name": "2013 Regular/Special Session",
            "classification": "primary",
            "identifier": "2013A",
            "name": "2013 Regular Session",
            "start_date": "2013-01-09",
            "end_date": "2013-05-09",
        },
        {
            "_scraped_name": "2014 Legislative Session",
            "classification": "primary",
            "identifier": "2014A",
            "name": "2014 Regular Session",
            "start_date": "2014-01-08",
            "end_date": "2014-05-07",
        },
        {
            "_scraped_name": "2015 Legislative Session",
            "classification": "primary",
            "identifier": "2015A",
            "name": "2015 Regular Session",
            "start_date": "2015-01-07",
            "end_date": "2015-05-06",
        },
        {
            "_scraped_name": "2016 Legislative Session",
            "classification": "primary",
            "identifier": "2016A",
            "name": "2016 Regular Session",
            "start_date": "2016-01-13",
            "end_date": "2016-05-11",
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "identifier": "2017A",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11",
            "end_date": "2017-05-10",
        },
        {
            "_scraped_name": "8017 First Extraordinary Session",
            "classification": "special",
            "identifier": "2017B",
            "name": "2017 First Extraordinary Session",
            "start_date": "2017-10-02",
            "end_date": "2017-10-06",
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "identifier": "2018A",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10",
            "end_date": "2018-03-11",
        },
        {
            "_scraped_name": "2019 Regular Session",
            "classification": "primary",
            "identifier": "2019A",
            "name": "2019 Regular Session",
            "start_date": "2019-01-04",
            "end_date": "2019-05-03",
        },
        {
            "_scraped_name": "2020 Regular Session",
            "classification": "primary",
            "identifier": "2020A",
            "name": "2020 Regular Session",
            "start_date": "2020-01-08",
            "end_date": "2020-05-06",
        },
    ]
    ignored_scraped_sessions = [
        "2013 Legislative Session",
        "2012 First Special Session",
        "2012 Legislative Session",
        "2011 Legislative Session",
        "2010 Legislative Session",
        "2009 Legislative Session",
        "2008 Legislative Session",
        "2007 Legislative Session",
        "2006 First Special Session",
        "2006 Legislative Session",
        "2005 Legislative Session",
        "2004 Legislative Session",
        "2003 Legislative Session",
        "2002 First Special Session",
        "2002 Legislative Session",
        "2001 Second Special Session",
        "2001 First Special Session",
        "2001 Legislative Session",
        "2000 Legislative Session",
        "2010 Regular/Special Session",
    ]

    def get_session_list(self):
        sessions = []
        regex = r"2[0-9][0-9][0-9]\ .*\ Session"

        tags = url_xpath(
            "http://www.leg.state.co.us/clics/cslFrontPages.nsf/PrevSessionInfo?OpenForm",
            "//font/text()",
        )
        for tag in tags:
            sess = re.findall(regex, tag)
            for session in sess:
                sessions.append(session)

        return sessions
