from .people import SCPersonScraper
from .bills import SCBillScraper
from .events import SCEventScraper
from openstates.utils import State
import requests
import lxml.html


class SouthCarolina(State):
    scrapers = {
        "people": SCPersonScraper,
        "bills": SCBillScraper,
        "events": SCEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "119 - (2011-2012)",
            "classification": "primary",
            "identifier": "119",
            "name": "2011-2012 Regular Session",
            "start_date": "2010-11-17",
        },
        {
            "_scraped_name": "120 - (2013-2014)",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session",
            "start_date": "2013-01-08",
        },
        {
            "_scraped_name": "121 - (2015-2016)",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session",
            "start_date": "2015-01-13",
        },
        {
            "_scraped_name": "122 - (2017-2018)",
            "classification": "primary",
            "end_date": "2018-05-09",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-10",
        },
        {
            "_scraped_name": "123 - (2019-2020)",
            "classification": "primary",
            "end_date": "2019-05-09",
            "identifier": "2019-2020",
            "name": "2019-2020 Regular Session",
            "start_date": "2019-01-09",
        },
    ]
    ignored_scraped_sessions = [
        "118 - (2009-2010)",
        "117 - (2007-2008)",
        "116 - (2005-2006)",
        "115 - (2003-2004)",
        "114 - (2001-2002)",
        "113 - (1999-2000)",
        "112 - (1997-1998)",
        "111 - (1995-1996)",
        "110 - (1993-1994)",
        "109 - (1991-1992)",
        "108 - (1989-1990)",
        "107 - (1987-1988)",
        "106 - (1985-1986)",
        "105 - (1983-1984)",
        "104 - (1981-1982)",
        "103 - (1979-1980)",
        "102 - (1977-1978)",
        "101 - (1975-1976)",
    ]

    def get_session_list(self):
        """ Get session list from billsearch page using xpath"""
        url = "http://www.scstatehouse.gov/billsearch.php"
        path = "//select[@id='session']/option/text()"

        doc = lxml.html.fromstring(requests.get(url).text)
        return doc.xpath(path)
