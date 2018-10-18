from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import PABillScraper
# from .events import PAEventScraper
# from .people import PALegislatorScraper
# from .committees import PACommitteeScraper

settings = {'SCRAPELIB_RPM': 30}


class Pennsylvania(Jurisdiction):
    division_id = "ocd-division/country:us/state:pa"
    classification = "government"
    name = "Pennsylvania"
    url = "http://www.legis.state.pa.us/"
    scrapers = {
        'bills': PABillScraper,
        # 'events': PAEventScraper,
        # 'people': PALegislatorScraper,
        # 'committees': PACommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-2010 Regular Session",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session"
        },
        {
            "_scraped_name": "2009-2010 Special Session #1 (Transportation)",
            "classification": "special",
            "identifier": "2009-2010 Special Session #1 (Transportation)",
            "name": "2009-2010, 1st Special Session"
        },
        {
            "_scraped_name": "2011-2012 Regular Session",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-2014 Regular Session",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016 Regular Session",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018 Regular Session",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-03",
            "end_date": "2017-12-31"
        }
    ]
    ignored_scraped_sessions = [
        "1965-1966 Special Session #1",
        "1965-1966 Special Session #2",
        "1965-1966 Special Session #3",
        "1963-1964 Regular Session",
        "1963-1964 Special Session #1",
        "1963-1964 Special Session #2",
        "1961-1962 Regular Session",
        "1961-1962 Special Session #1",
        "1959-1960 Regular Session",
        "1957-1958 Regular Session",
        "1955-1956 Regular Session",
        "1953-1954 Regular Session",
        "1951-1952 Regular Session",
        "1949-1950 Regular Session",
        "1947-1948 Regular Session",
        "1945-1946 Regular Session",
        "1943-1944 Regular Session",
        "1941-1942 Regular Session",
        "1939-1940 Regular Session",
        "1937-1938 Regular Session",
        "1935-1936 Regular Session",
        "1933-1934 Regular Session",
        "1931-1932 Regular Session",
        "1929-1930 Regular Session",
        "1927-1928 Regular Session",
        "1925-1926 Regular Session",
        "1923-1924 Regular Session",
        "1921-1922 Regular Session",
        "1919-1920 Regular Session",
        "1917-1918 Regular Session",
        "1915-1916 Regular Session",
        "1913-1914 Regular Session",
        "1911-1912 Regular Session",
        "1909-1910 Regular Session",
        "1907-1908 Regular Session",
        "1905-1906 Regular Session",
        "1903-1904 Regular Session",
        "1901-1902 Regular Session",
        "1899-1900 Regular Session",
        "1897-1898 Regular Session",
        "1895-1896 Regular Session",
        "1893-1894 Regular Session",
        "1891-1892 Regular Session",
        "1889-1890 Regular Session",
        "1887-1888 Regular Session",
        "1885-1886 Regular Session",
        "1883-1884 Regular Session",
        "1881-1882 Regular Session",
        "1879-1880 Regular Session",
        "1877-1878 Regular Session",
        "1875-1876 Regular Session",
        "1873-1874 Regular Session",
        "1871-1872 Regular Session",
        "1869-1870 Regular Session",
        "1867-1868 Regular Session",
        "1865-1866 Regular Session",
        "1863-1864 Regular Session",
        "1861-1862 Regular Session",
        "1859-1860 Regular Session",
        "1857-1858 Regular Session",
        "1855-1856 Regular Session",
        "1853-1854 Regular Session",
        "1851-1852 Regular Session",
        "1849-1850 Regular Session",
        "1847-1848 Regular Session",
        "1845-1846 Regular Session",
        "1843-1844 Regular Session",
        "1841-1842 Regular Session",
        "1839-1840 Regular Session",
        "1837-1838 Regular Session",
        "1835-1836 Regular Session",
        "1833-1834 Regular Session",
        "1831-1832 Regular Session",
        "1829-1830 Regular Session",
        "1827-1828 Regular Session",
        "1825-1826 Regular Session",
        "1823-1824 Regular Session",
        "1821-1822 Regular Session",
        "1819-1820 Regular Session",
        "1817-1818 Regular Session",
        "1815-1816 Regular Session",
        "1813-1814 Regular Session",
        "1811-1812 Regular Session",
        "1809-1810 Regular Session",
        "1807-1808 Regular Session",
        "1805-1806 Regular Session",
        "1803-1804 Regular Session",
        "1801-1802 Regular Session",
        "1965-1966 Regular Session",
        "1967-1968 Regular Session",
        "1969-1970 Regular Session",
        "1971-1972 Regular Session",
        "1971-1972 Special Session #1",
        "1971-1972 Special Session #2",
        "1973-1974 Regular Session",
        "1975-1976 Regular Session",
        "1977-1978 Regular Session",
        "1979-1980 Regular Session",
        "1981-1982 Regular Session",
        "1983-1984 Regular Session",
        "1985-1986 Regular Session",
        "1987-1988 Regular Session",
        "1987-1988 Special Session #1",
        "1989-1990 Regular Session",
        "1991-1992 Regular Session",
        "1991-1992 Special Session #1",
        "1993-1994 Regular Session",
        "1995-1996 Regular Session",
        "1995-1996 Special Session #1",
        "1995-1996 Special Session #2",
        "1997-1998 Regular Session",
        "1999-2000 Regular Session",
        "2001-2002 Regular Session",
        "2001-2002 Special Session #1",
        "2003-2004 Regular Session",
        "2005-2006 Regular Session",
        "2005-2006 Special Session #1 (taxpayer relief act)",
        "2007-2008 Regular Session",
        "2007-2008 Special Session #1 (Energy Policy)",
        # Different nomenclature, for sessions already in this list
        "1962 Regular Session",
        "1963 Regular Session",
        "1963 Special Session #1",
        "1963 Special Session #2",
        "1964 Regular Session",
        "1965 Regular Session",
        "1966 Regular Session",
        "1965 Special Session #1",
        "1965 Special Session #3",
        "1966 Special Session #1",
        "1966 Special Session #3",
    ]

    def get_organizations(self):
        legislature_name = "Pennsylvania General Assembly"
        lower_chamber_name = "House"
        lower_seats = 203
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

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        # PA keeps slowly adding backdata, so just ignore it en masse
        for i in range(1800, 2000):
            self.ignored_scraped_sessions.append('{} Regular Session'.format(i))
            self.ignored_scraped_sessions.append('{} Special Session #1'.format(i))

        return url_xpath('http://www.legis.state.pa.us/cfdocs/legis/home/bills/',
                         '//select[@id="billSessions"]/option/text()')
