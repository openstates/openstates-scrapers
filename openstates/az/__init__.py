import lxml.html
import re
import requests

from pupa.scrape import Jurisdiction, Organization

from .people import AZPersonScraper

# from .committees import AZCommitteeScraper
# from .events import AZEventScraper
from .bills import AZBillScraper


class Arizona(Jurisdiction):
    division_id = "ocd-division/country:us/state:az"
    classification = "government"
    name = "Arizona"
    url = "http://www.azleg.gov/"
    scrapers = {
        "people": AZPersonScraper,
        # 'committees': AZCommitteeScraper,
        # 'events': AZEventScraper,
        "bills": AZBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - First Regular Session",
            "classification": "primary",
            "end_date": "2009-07-01",
            "identifier": "49th-1st-regular",
            "name": "49th Legislature, 1st Regular Session (2009)",
            "start_date": "2009-01-12",
        },
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - First Special Session",
            "classification": "special",
            "end_date": "2009-01-31",
            "identifier": "49th-1st-special",
            "name": "49th Legislature, 1st Special Session (2009)",
            "start_date": "2009-01-28",
        },
        {
            "_scraped_name": "2010 - Forty-ninth Legislature - Second Regular Session",
            "classification": "primary",
            "end_date": "2010-04-29",
            "identifier": "49th-2nd-regular",
            "name": "49th Legislature, 2nd Regular Session (2010)",
            "start_date": "2010-01-11",
        },
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - Second Special Session",
            "classification": "special",
            "end_date": "2009-05-27",
            "identifier": "49th-2nd-special",
            "name": "49th Legislature, 2nd Special Session (2009)",
            "start_date": "2009-05-21",
        },
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - Third Special Session",
            "classification": "special",
            "end_date": "2009-08-25",
            "identifier": "49th-3rd-special",
            "name": "49th Legislature, 3rd Special Session (2009)",
            "start_date": "2009-07-06",
        },
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - Fourth Special Session",
            "classification": "special",
            "end_date": "2009-11-23",
            "identifier": "49th-4th-special",
            "name": "49th Legislature, 4th Special Session (2009)",
            "start_date": "2009-11-17",
        },
        {
            "_scraped_name": "2009 - Forty-ninth Legislature - Fifth Special Session",
            "classification": "special",
            "end_date": "2009-12-19",
            "identifier": "49th-5th-special",
            "name": "49th Legislature, 5th Special Session (2009)",
            "start_date": "2009-12-17",
        },
        {
            "_scraped_name": "2010 - Forty-ninth Legislature - Sixth Special Session",
            "classification": "special",
            "end_date": "2010-02-11",
            "identifier": "49th-6th-special",
            "name": "49th Legislature, 6th Special Session (2010)",
            "start_date": "2010-02-01",
        },
        {
            "_scraped_name": "2010 - Forty-ninth Legislature - Seventh Special Session",
            "classification": "special",
            "end_date": "2010-03-16",
            "identifier": "49th-7th-special",
            "name": "49th Legislature, 7th Special Session (2010)",
            "start_date": "2010-03-08",
        },
        {
            "_scraped_name": "2010 - Forty-ninth Legislature - Eighth Special Session",
            "classification": "special",
            "end_date": "2010-04-01",
            "identifier": "49th-8th-special",
            "name": "49th Legislature, 8th Special Session (2010)",
            "start_date": "2010-03-29",
        },
        {
            "_scraped_name": "2010 - Forty-ninth Legislature - Ninth Special Session",
            "classification": "special",
            "end_date": "2010-08-11",
            "identifier": "49th-9th-special",
            "name": "49th Legislature, 9th Special Session (2010)",
            "start_date": "2010-08-09",
        },
        {
            "_scraped_name": "2011 - Fiftieth Legislature - First Regular Session",
            "classification": "primary",
            "end_date": "2011-04-20",
            "identifier": "50th-1st-regular",
            "name": "50th Legislature, 1st Regular Session (2011)",
            "start_date": "2011-01-10",
        },
        {
            "_scraped_name": "2011 - Fiftieth Legislature - First Special Session",
            "classification": "special",
            "end_date": "2011-01-20",
            "identifier": "50th-1st-special",
            "name": "50th Legislature, 1st Special Session (2011)",
            "start_date": "2011-01-19",
        },
        {
            "_scraped_name": "2012 - Fiftieth Legislature - Second Regular Session",
            "classification": "primary",
            "identifier": "50th-2nd-regular",
            "name": "50th Legislature, 2nd Regular Session (2012)",
        },
        {
            "_scraped_name": "2011 - Fiftieth Legislature - Second Special Session",
            "classification": "special",
            "end_date": "2011-02-16",
            "identifier": "50th-2nd-special",
            "name": "50th Legislature, 2nd Special Session (2011)",
            "start_date": "2011-02-14",
        },
        {
            "_scraped_name": "2011 - Fiftieth Legislature - Third Special Session",
            "classification": "special",
            "end_date": "2011-06-13",
            "identifier": "50th-3rd-special",
            "name": "50th Legislature, 3rd Special Session (2011)",
            "start_date": "2011-06-10",
        },
        {
            "_scraped_name": "2011 - Fiftieth Legislature - Fourth Special Session",
            "classification": "special",
            "end_date": "2011-11-01",
            "identifier": "50th-4th-special",
            "name": "50th Legislature, 4th Special Session (2011)",
            "start_date": "2011-11-01",
        },
        {
            "_scraped_name": "2013 - Fifty-first Legislature - First Regular Session",
            "classification": "primary",
            "identifier": "51st-1st-regular",
            "name": "51st Legislature - 1st Regular Session (2013)",
        },
        {
            "_scraped_name": "2013 - Fifty-first Legislature - First Special Session",
            "classification": "primary",
            "identifier": "51st-1st-special",
            "name": "51st Legislature - 1st Special Session (2013)",
        },
        {
            "_scraped_name": "2014 - Fifty-first Legislature - Second Regular Session",
            "classification": "primary",
            "identifier": "51st-2nd-regular",
            "name": "51st Legislature - 2nd Regular Session",
        },
        {
            "_scraped_name": "2014 - Fifty-first Legislature - Second Special Session",
            "classification": "special",
            "identifier": "51st-2nd-special",
            "name": "51st Legislature - 2nd Special Session",
        },
        {
            "_scraped_name": "2015 - Fifty-second Legislature - First Regular Session",
            "classification": "primary",
            "identifier": "52nd-1st-regular",
            "name": "52nd Legislature - 1st Regular Session",
        },
        {
            "_scraped_name": "2015 - Fifty-second Legislature - First Special Session",
            "classification": "special",
            "identifier": "52nd-1st-special",
            "name": "52nd Legislature - 1st Special Session",
        },
        {
            "_scraped_name": "2016 - Fifty-second Legislature - Second Regular Session",
            "classification": "primary",
            "identifier": "52nd-2nd-regular",
            "name": "52nd Legislature - 2nd Regular Session",
        },
        {
            "_scraped_name": "2017 - Fifty-third Legislature - First Regular Session",
            "classification": "primary",
            "end_date": "2017-05-03",
            "identifier": "53rd-1st-regular",
            "name": "53rd Legislature - 1st Regular Session",
            "start_date": "2017-01-09",
        },
        {
            "_scraped_name": "2018 - Fifty-third Legislature - First Special Session",
            "classification": "special",
            "identifier": "53rd-1st-special",
            "name": "53rd Legislature - 1st Special Session",
        },
        {
            "_scraped_name": "2018 - Fifty-third Legislature - Second Regular Session",
            "classification": "primary",
            "identifier": "53rd-2nd-regular",
            "name": "53rd Legislature - 2nd Regular Session",
            "start_date": "2018-01-08",
            "end_date": "2018-05-03",
        },
        {
            "_scraped_name": "2019 - Fifty-fourth Legislature - First Regular Session",
            "classification": "primary",
            "identifier": "54th-1st-regular",
            "name": "54th Legislature - 1st Regular Session",
            "start_date": "2019-01-14",
            "end_date": "2019-03-29",
        },
        {
            "_scraped_name": "2020 - Fifty-fourth Legislature - Second Regular Session",
            "classification": "primary",
            "identifier": "54th-2nd-regular",
            "name": "54th Legislature - 2nd Regular Session",
            "start_date": "2020-01-13",
        },
    ]
    ignored_scraped_sessions = [
        "2008 - Forty-eighth Legislature - Second Regular Session",
        "2007 - Forty-eighth Legislature - First Regular Session",
        "2006 - Forty-seventh Legislature - First Special Session",
        "2006 - Forty-seventh Legislature - Second Regular Session",
        "2005 - Forty-seventh Legislature - First Regular Session",
        "2004 - Forty-sixth Legislature - Second Regular Session",
        "2003 - Forty-sixth Legislature - Second Special Session",
        "2003 - Forty-sixth Legislature - First Special Session",
        "2003 - Forty-sixth Legislature - First Regular Session",
        "2002 - Forty-fifth Legislature - Sixth Special Session",
        "2002 - Forty-fifth Legislature - Fifth Special Session",
        "2002 - Forty-fifth Legislature - Fourth Special Session",
        "2002 - Forty-fifth Legislature - Third Special Session",
        "2002 - Forty-fifth Legislature - Second Regular Session",
        "2001 - Forty-fifth Legislature - Second Special Session",
        "2001 - Forty-fifth Legislature - First Special Session",
        "2001 - Forty-fifth Legislature - First Regular Session",
        "2000 - Forty-fourth Legislature - Seventh Special Session",
        "2000 - Forty-fourth Legislature - Sixth Special Session",
        "2000 - Forty-fourth Legislature - Fifth Special Session",
        "2000 - Forty-fourth Legislature - Fourth Special Session",
        "2000 - Forty-fourth Legislature - Second Regular Session",
        "1999 - Forty-fourth Legislature - Third Special Session",
        "1999 - Forty-fourth Legislature - Second Special Session",
        "1999 - Forty-fourth Legislature - First Special Session",
        "1999 - Forty-fourth Legislature - First Regular Session",
        "1998 - Forty-third Legislature - Sixth Special Session",
        "1998 - Forty-third Legislature - Fifth Special Session",
        "1998 - Forty-third Legislature - Fourth Special Session",
        "1998 - Forty-third Legislature - Third Special Session",
        "1998 - Forty-third Legislature - Second Regular Session",
        "1997 - Forty-third Legislature - Second Special Session",
        "1997 - Forty-third Legislature - First Special Session",
        "1997 - Forty-third Legislature - First Regular Session",
        "1996 - Forty-second Legislature - Seventh Special Session",
        "1996 - Forty-second Legislature - Sixth Special Session",
        "1996 - Forty-second Legislature - Fifth Special Session",
        "1996 - Forty-second Legislature - Second Regular Session",
        "1995 - Forty-second Legislature - Fourth Special Session",
        "1995 - Forty-second Legislature - Third Special Session",
        "1995 - Forty-Second Legislature - Second Special Session",
        "1995 - Forty-Second Legislature - First Special Session",
        "1995 - Forty-second Legislature - First Regular Session",
        "1994 - Forty-first Legislature - Ninth Special Session",
        "1994 - Forty-first Legislature - Eighth Special Session",
        "1994 - Forty-first Legislature - Second Regular Session",
        "1993 - Forty-first Legislature - Seventh Special Session",
        "1993 - Forty-first Legislature - Sixth Special Session",
        "1993 - Forty-first Legislature - Fifth Special Session",
        "1993 - Forty-first Legislature - Fourth Special Session",
        "1993 - Forty-first Legislature - Third Special Session",
        "1993 - Forty-first Legislature - Second Special Session",
        "1993 - Forty-first Legislature - First Special Session",
        "1993 - Forty-first Legislature - First Regular Session",
        "1992 - Fortieth Legislature - Ninth Special Session",
        "1992 - Fortieth Legislature - Eighth Special Session",
        "1992 - Fortieth Legislature - Seventh Special Session",
        "1992 - Fortieth Legislature - Fifth Special Session",
        "1992 - Fortieth Legislature - Sixth Special Session",
        "1992 - Fortieth Legislature - Second Regular Session",
        "1991 - Fortieth Legislature - Fourth Special Session",
        "1991 - Fortieth Legislature - Third Special Session",
        "1991 - Fortieth Legislature - Second Special Session",
        "1991 - Fortieth Legislature - First Special Session",
        "1991 - Fortieth Legislature - First Regular Session",
        "1990 - Thirty-ninth Legislature - Fifth Special Session",
        "1990 - Thirty-ninth Legislature - Fourth Special Session",
        "1990 - Thirty-ninth Legislature - Third Special Session",
        "1990 - Thirty-ninth Legislature - Second Regular Session",
        "1989 - Thirty-ninth Legislature - Second Special Session",
        "1989 - Thirty-ninth Legislature - First Special Session",
        "1989 - Thirty-ninth Legislature - First Regular Session",
    ]

    def get_organizations(self):
        legislature_name = "Arizona State Legislature"

        legislature = Organization(name=legislature_name, classification="legislature")
        upper = Organization(
            "Senate", classification="upper", parent_id=legislature._id
        )
        lower = Organization("House", classification="lower", parent_id=legislature._id)

        yield Organization("Office of the Governor", classification="executive")
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        session = requests.Session()

        data = session.get("https://www.azleg.gov/")

        # TODO: JSON at https://apps.azleg.gov/api/Session/

        doc = lxml.html.fromstring(data.text)
        sessions = doc.xpath("//select/option/text()")
        sessions = [re.sub(r"\(.+$", "", x).strip() for x in sessions]
        return sessions
