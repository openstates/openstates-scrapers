from utils import url_xpath
from openstates.scrape import State
from .bills import DEBillScraper
from .events import DEEventScraper


class Delaware(State):
    scrapers = {
        "bills": DEBillScraper,
        "events": DEEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "1998 - 2000 (GA 140)",
            "identifier": "140",
            "name": "140th General Assembly (1999-2000)",
            "start_date": "1999-01-05",
            "end_date": "2001-01-01",
        },
        {
            "_scraped_name": "2000 - 2002 (GA 141)",
            "identifier": "141",
            "name": "141st General Assembly (2001-2002)",
            "start_date": "2001-01-02",
            "end_date": "2003-01-01",
        },
        {
            "_scraped_name": "2002 - 2004 (GA 142)",
            "identifier": "142",
            "name": "142nd General Assembly (2003-2004)",
            "start_date": "2003-01-07",
            "end_date": "2005-01-01",
        },
        {
            "_scraped_name": "2004 - 2006 (GA 143)",
            "identifier": "143",
            "name": "143rd General Assembly (2005-2006)",
            "start_date": "2005-01-04",
            "end_date": "2007-01-01",
        },
        {
            "_scraped_name": "2006 - 2008 (GA 144)",
            "identifier": "144",
            "name": "144th General Assembly (2007-2008)",
            "start_date": "2007-01-09",
            "end_date": "2009-01-01",
        },
        {
            "_scraped_name": "2008 - 2010 (GA 145)",
            "identifier": "145",
            "name": "145th General Assembly (2009-2010)",
            "start_date": "2009-01-06",
            "end_date": "2010-05-05",
        },
        {
            "_scraped_name": "2010 - 2012 (GA 146)",
            "identifier": "146",
            "name": "146th General Assembly (2011-2012)",
            "start_date": "2011-01-05",
            "end_date": "2012-05-09",
        },
        {
            "_scraped_name": "2012 - 2014 (GA 147)",
            "identifier": "147",
            "name": "147th General Assembly (2013-2014)",
            "start_date": "2013-01-09",
            "end_date": "2014-05-07",
        },
        {
            "_scraped_name": "2014 - 2016 (GA 148)",
            "identifier": "148",
            "name": "148th General Assembly (2015-2016)",
            "start_date": "2015-01-07",
            "end_date": "2016-05-04",
        },
        {
            "_scraped_name": "2016 - 2018 (GA 149)",
            "identifier": "149",
            "name": "149th General Assembly (2017-2018)",
            "start_date": "2017-01-10",
            "end_date": "2018-06-30",
        },
        {
            "_scraped_name": "2018 - 2020 (GA 150)",
            "identifier": "150",
            "name": "150th General Assembly (2019-2020)",
            "start_date": "2019-01-08",
            "end_date": "2020-06-30",
        },
        {
            "_scraped_name": "2020 - 2022 (GA 151)",
            "identifier": "151",
            "name": "151st General Assembly (2021-2022)",
            "start_date": "2021-01-12",
            "end_date": "2022-06-30",
            "active": False,
        },
        {
            "_scraped_name": "2022 - 2024 (GA 152)",
            "identifier": "152",
            "name": "152nd General Assembly (2023-2024)",
            "start_date": "2022-01-10",
            "end_date": "2022-06-30",
            "active": True,
        },
    ]
    ignored_scraped_sessions = [
        "1932 - 1934 (GA 104)",
        "1928 - 1930 (GA 102)",
        "1930 - 1932 (GA 103)",
        "1918 - 1920 (GA 97)",
        "1880 - 1882 (GA 78)",
        "1902 - 1904 (GA 89)",
        "1896 - 1898 (GA 86)",
        "1878 - 1880 (GA 77)",
        "1904 - 1906 (GA 90)",
        "1916 - 1918 (GA 96)",
        "1912 - 1914 (GA 94)",
        "1924 - 1926 (GA 100)",
        "1892 - 1894 (GA 84)",
        "1882 - 1884 (GA 79)",
        "1886 - 1888 (GA 81)",
        "1890 - 1892 (GA 83)",
        "1920 - 1922 (GA 98)",
        "1906 - 1908 (GA 91)",
        "1910 - 1912 (GA 93)",
        "1898 - 1900 (GA 87)",
        "1900 - 1902 (GA 88)",
        "1908 - 1910 (GA 92)",
        "1884 - 1886 (GA 80)",
        "1926 - 1928 (GA 101)",
        "1894 - 1896 (GA 85)",
        "1914 - 1916 (GA 95)",
        "1922 - 1924 (GA 99)",
        "1888 - 1890 (GA 82)",
        "1876 - 1878 (GA 76)",
    ]

    def get_session_list(self):
        url = "https://legis.delaware.gov/"
        sessions = url_xpath(
            url, '//select[@id="billSearchGARefiner"]/option/text()', verify=False
        )
        sessions = [session.strip() for session in sessions if session.strip()]
        return sessions
