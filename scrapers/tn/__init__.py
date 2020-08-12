from utils import url_xpath, State
from .bills import TNBillScraper
from .events import TNEventScraper
from .people import TNPersonScraper

# from .committees import TNCommitteeScraper


class Tennessee(State):
    scrapers = {
        "bills": TNBillScraper,
        # 'committees': TNCommitteeScraper,
        "events": TNEventScraper,
        "people": TNPersonScraper,
    }
    legislative_sessions = [
        # {
        #     "_scraped_name": "106th General Assembly",
        #     "classification": "primary",
        #     "identifier": "106",
        #     "name": "106th Regular Session (2009-2010)"
        #     "start_date": "2009-01-13",
        #     "end_date": "2010-06-10",
        # },
        {
            "_scraped_name": "107th General Assembly",
            "classification": "primary",
            "identifier": "107",
            "name": "107th Regular Session (2011-2012)",
            "start_date": "2011-01-11",
            "end_date": "2012-05-01",
        },
        {
            "_scraped_name": "108th General Assembly",
            "classification": "primary",
            "identifier": "108",
            "name": "108th Regular Session (2013-2014)",
            "start_date": "2013-01-08",
            "end_date": "2014-04-18",
        },
        {
            "_scraped_name": "109th General Assembly",
            "classification": "primary",
            "identifier": "109",
            "name": "109th Regular Session (2015-2016)",
            "start_date": "2015-01-13",
            "end_date": "2016-04-22",
        },
        {
            "_scraped_name": "1st Extraordinary Session (February 2015)",
            "classification": "special",
            "identifier": "109s1",
            "name": "109th First Extraordinary Session (February 2016)",
            "start_date": "2016-02-01",
            "end_date": "2016-02-29",
        },
        {
            "_scraped_name": "2nd Extraordinary Session (September 2016)",
            "classification": "special",
            "identifier": "109s2",
            "name": "109th Second Extraordinary Session (September 2016)",
            "start_date": "2016-09-12",
            "end_date": "2016-09-14",
        },
        {
            "_scraped_name": "110th General Assembly",
            "classification": "primary",
            "identifier": "110",
            "name": "110th Regular Session (2017-2018)",
            "start_date": "2017-01-10",
            "end_date": "2018-04-27",
        },
        {
            "_scraped_name": "111th General Assembly",
            "classification": "primary",
            "identifier": "111",
            "name": "111th Regular Session (2019-2020)",
            "start_date": "2019-01-09",
            "end_date": "2020-06-19",
        },
        {
            # This is shortened as it's used to find the link within the archive page. That page
            # has a line break after "Session" so XPath was not finding it.
            "_scraped_name": "First Extraordinary Session",
            "classification": "special",
            "identifier": "111S1",
            "name": "111th First Extraordinary Session (August 2019)",
            "start_date": "2020-08-05",
            # TODO: Add real end date after session
            "end_date": "2020-08-14",
        },
        {
            "_scraped_name": "Second Extraordinary Session (August 2020)",
            "classification": "special",
            "identifier": "111S2",
            "name": "111th Second Extraordinary Session (August 2020)",
            "start_date": "2020-08-05",
            # TODO: Add real end date after session
            "end_date": "2020-08-14",
        },
    ]
    ignored_scraped_sessions = [
        "107th General Assembly",
        "106th General Assembly",
        "105th General Assembly",
        "104th General Assembly",
        "103rd General Assembly",
        "102nd General Assembly",
        "101st General Assembly",
        "100th General Assembly",
        "99th General Assembly",
    ]

    def get_session_list(self):
        # Special sessions are available in the archive, but not in current session.
        # Solution is to scrape special session as part of regular session
        return [
            x
            for x in url_xpath(
                "http://www.capitol.tn.gov/legislation/archives.html",
                '//h2[text()="Bills and Resolutions"]/following-sibling::ul/li/text()',
            )
            if x.strip()
        ]

    @property
    def sessions_by_id(self):
        """A map of sessions in legislative_sessions indexed by their `identifer`"""
        if hasattr(self, "_sessions_by_id"):
            return self._sessions_by_id

        self._sessions_by_id = {
            session["identifier"]: session for session in self.legislative_sessions
        }

        return self._sessions_by_id
