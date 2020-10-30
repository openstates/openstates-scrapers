from utils import url_xpath, State

from .bills import MNBillScraper
from .people import MNPersonScraper
from .vote_events import MNVoteScraper

# from .committees import MNCommitteeScraper
# from .events import MNEventScraper

"""
Minnesota legislative data can be found at the Office of the Revisor
of Statutes:
https://www.revisor.mn.gov/

Votes:
There are not detailed vote data for Senate votes, simply yes and no counts.
Bill pages have vote counts and links to House details, so it makes more
sense to get vote data from the bill pages.
"""


class Minnesota(State):
    scrapers = {
        "bills": MNBillScraper,
        # "committees": MNCommitteeScraper,
        "people": MNPersonScraper,
        "votes": MNVoteScraper,
        # "events": MNEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "86th Legislature, 2009-2010",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session",
            "start_date": "2009-01-06",
            "end_date": "2011-01-04",
        },
        {
            "_scraped_name": "86th Legislature, 2010 1st Special Session",
            "classification": "special",
            "identifier": "2010 1st Special Session",
            "name": "2010, 1st Special Session",
            "start_date": "2010-05-17",
            "end_date": "2010-05-17",
        },
        {
            "_scraped_name": "86th Legislature, 2010 2nd Special Session",
            "classification": "special",
            "identifier": "2010 2nd Special Session",
            "name": "2010, 2nd Special Session",
            "start_date": "2010-10-18",
            "end_date": "2010-10-18",
        },
        {
            "_scraped_name": "87th Legislature, 2011-2012",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session",
            "start_date": "2011-01-04",
            "end_date": "2012-05-10",
        },
        {
            "_scraped_name": "87th Legislature, 2011 1st Special Session",
            "classification": "special",
            "identifier": "2011s1",
            "name": "2011, 1st Special Session",
            "start_date": "2011-07-19",
            "end_date": "2011-07-20",
        },
        {
            "_scraped_name": "87th Legislature, 2012 1st Special Session",
            "classification": "special",
            "identifier": "2012s1",
            "name": "2012, 1st Special Session",
            "start_date": "2011-08-24",
            "end_date": "2011-08-24",
        },
        {
            "_scraped_name": "88th Legislature, 2013-2014",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-08",
            "end_date": "2014-05-16",
        },
        {
            "_scraped_name": "88th Legislature, 2013 1st Special Session",
            "classification": "special",
            "identifier": "2013s1",
            "name": "2013, 1st Special Session",
            "start_date": "2013-09-09",
            "end_date": "2013-09-09",
        },
        {
            "_scraped_name": "89th Legislature, 2015-2016",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-06",
            "end_date": "2016-05-23",
        },
        {
            "_scraped_name": "89th Legislature, 2015 1st Special Session",
            "classification": "special",
            "identifier": "2015s1",
            "name": "2015, 1st Special Session",
            "start_date": "2015-06-12",
            "end_date": "2015-06-13",
        },
        {
            "_scraped_name": "90th Legislature, 2017 1st Special Session",
            "classification": "special",
            "identifier": "2017s1",
            "name": "2017, 1st Special Session",
            "start_date": "2017-05-23",
            "end_date": "2017-05-30",
        },
        {
            "_scraped_name": "90th Legislature, 2017-2018",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-03",
            "end_date": "2018-05-20",
        },
        {
            "_scraped_name": "91st Legislature, 2019 1st Special Session",
            "classification": "primary",
            "identifier": "2019s1",
            "name": "2019, First Special Session",
            "start_date": "2019-05-24",
            "end_date": "2019-05-29",
        },
        {
            "_scraped_name": "91st Legislature, 2019-2020",
            "classification": "primary",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-08",
            "end_date": "2019-06-20",
        },
        {
            "_scraped_name": "91st Legislature, 2020 1st Special Session",
            "classification": "primary",
            "identifier": "2020s1",
            "name": "2020, First Special Session",
            "start_date": "2020-06-13",
            "end_date": "2020-06-19",
        },
        {
            "_scraped_name": "91st Legislature, 2020 2nd Special Session",
            "classification": "primary",
            "identifier": "2020s2",
            "name": "2020, Second Special Session",
            "start_date": "2020-07-13",
            "end_date": "2020-07-21",
        },
        {
            "_scraped_name": "91st Legislature, 2020 3rd Special Session",
            "classification": "primary",
            "identifier": "2020s3",
            "name": "2020, Third Special Session",
            "start_date": "2020-08-12",
            "end_date": "2020-08-12",
        },
        {
            "_scraped_name": "91st Legislature, 2020 4th Special Session",
            "classification": "primary",
            "identifier": "2020s4",
            "name": "2020, Fourth Special Session",
            "start_date": "2020-09-11",
            # Just a guess. TODO: set after end of special
            "end_date": "2020-09-11",
        },
        {
            "_scraped_name": "91st Legislature, 2020 5th Special Session",
            "classification": "special",
            "identifier": "2020s5",
            "name": "2020, Fifth Special Session",
            "start_date": "2020-09-16",
            # Just a guess. TODO: set after end of special
            "end_date": "2020-09-16",
        },
        #         {
        #             "_scraped_name": "92nd Legislature, 2021-2022",
        #             "classification": "primary",
        #             "identifier": "2021-2022",
        #             "name": "2021-2022 Regular Session",
        #             "start_date": "2021-01-16",
        #             # Just a guess. TODO: set after schedule is posted
        #             "end_date": "2021-06-01",
        #         },
    ]
    ignored_scraped_sessions = [
        "91st Legislature, 2020 6th Special Session",
        "92nd Legislature, 2021-2022",
        "85th Legislature, 2007-2008",
        "85th Legislature, 2007 1st Special Session",
        "84th Legislature, 2005-2006",
        "84th Legislature, 2005 1st Special Session",
        "83rd Legislature, 2003-2004",
        "83rd Legislature, 2003 1st Special Session",
        "82nd Legislature, 2001-2002",
        "82nd Legislature, 2002 1st Special Session",
        "82nd Legislature, 2001 1st Special Session",
        "81st Legislature, 1999-2000",
        "80th Legislature, 1997-1998",
        "80th Legislature, 1998 1st Special Session",
        "80th Legislature, 1997 3rd Special Session",
        "80th Legislature, 1997 2nd Special Session",
        "80th Legislature, 1997 1st Special Session",
        "79th Legislature, 1995-1996",
        "79th Legislature, 1995 1st Special Session",
    ]

    def get_session_list(self):
        return url_xpath(
            "https://www.revisor.mn.gov/bills/" "status_search.php?body=House",
            '//select[@name="session"]/option/text()',
        )
